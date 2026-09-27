import os, subprocess, uuid, shutil
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)
WORK_DIR = "work"
OUTPUT_DIR = "static/clips"
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

KEYWORDS = ["never", "crazy", "insane", "secret", "amazing", "worst", "best",
            "huge", "shocking", "unbelievable", "wow", "honestly", "literally"]

_whisper_model = None
def get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("base")
    return _whisper_model

def score_segment(seg):
    text = seg["text"].lower()
    score = text.count("!") * 2 + text.count("?")
    score += sum(1 for k in KEYWORDS if k in text) * 2
    score += 1 if len(text.split()) > 8 else 0
    return score

def build_clip_window(seg, segments, target_len=35):
    start, end = seg["start"], seg["end"]
    idx = segments.index(seg)
    i, j = idx, idx
    while (end - start) < target_len:
        grew = False
        if i > 0:
            i -= 1
            start = segments[i]["start"]
            grew = True
        if (end - start) < target_len and j < len(segments) - 1:
            j += 1
            end = segments[j]["end"]
            grew = True
        if not grew:
            break
    return start, end

def write_srt(path, segs, clip_start):
    def fmt(t):
        h, rem = int(t // 3600), t % 3600
        m, s = int(rem // 60), rem % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
    with open(path, "w") as f:
        idx = 1
        for s in segs:
            st, en = max(s["start"] - clip_start, 0), max(s["end"] - clip_start, 0)
            f.write(f"{idx}\n{fmt(st)} --> {fmt(en)}\n{s['text'].strip()}\n\n")
            idx += 1

def download_video(url, dest_path):
    """Try a few different strategies, since YouTube frequently blocks
    cloud-server IPs and changes its rules often."""
    attempts = [
        ["-f", "mp4/best", "--extractor-args", "youtube:player_client=android,web"],
        ["-f", "best", "--extractor-args", "youtube:player_client=android"],
        ["-f", "best"],
    ]
    last_error = None
    for extra_args in attempts:
        cmd = ["yt-dlp"] + extra_args + ["-o", dest_path, url]
        try:
            subprocess.run(cmd, check=True, timeout=900,
                            capture_output=True, text=True)
            return
        except subprocess.CalledProcessError as e:
            last_error = e.stderr or str(e)
    raise RuntimeError(last_error or "All download attempts failed.")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/clip", methods=["POST"])
def clip():
    url = request.form.get("url", "").strip()
    try:
        num_clips = int(request.form.get("num_clips", 3))
    except ValueError:
        num_clips = 3
    if not url:
        return jsonify({"error": "Paste a video link first."}), 400

    job_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(WORK_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    source_path = os.path.join(job_dir, "source.mp4")

    try:
        download_video(url, source_path)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": f"Couldn't download that video. YouTube may be blocking this server right now — try a different video, or try again in a bit. ({e})"}), 400

    try:
        model = get_model()
        result = model.transcribe(source_path, verbose=False)
        segments = result["segments"]
        if not segments:
            return jsonify({"error": "Couldn't find any speech in that video."}), 400

        for seg in segments:
            seg["score"] = score_segment(seg)
        ranked = sorted(segments, key=lambda s: s["score"], reverse=True)

        chosen, used = [], []
        for seg in ranked:
            if len(chosen) >= num_clips:
                break
            start, end = build_clip_window(seg, segments)
            if any(not (end <= u[0] or start >= u[1]) for u in used):
                continue
            chosen.append((start, end))
            used.append((start, end))
        chosen.sort()

        clip_urls = []
        out_job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(out_job_dir, exist_ok=True)
        for n, (start, end) in enumerate(chosen, 1):
            dur = end - start
            clip_segs = [s for s in segments if s["start"] < end and s["end"] > start]
            srt_path = os.path.join(job_dir, f"clip{n}.srt")
            write_srt(srt_path, clip_segs, start)
            out_path = os.path.join(out_job_dir, f"clip{n}.mp4")
            vf = (
                "crop=ih*9/16:ih,scale=1080:1920,"
                f"subtitles={srt_path}:force_style='FontSize=18,PrimaryColour=&H00FFFFFF&,Alignment=2,MarginV=80'"
            )
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start), "-i", source_path,
                "-t", str(dur), "-vf", vf, "-c:v", "libx264", "-c:a", "aac", out_path
            ], check=True, timeout=300)
            clip_urls.append(f"/static/clips/{job_id}/clip{n}.mp4")

        return jsonify({"clips": clip_urls})
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
