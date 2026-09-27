# Clipforge — put this live, free

## 1. Put the code on GitHub (free)
- Go to github.com, make a free account.
- Click "New repository," name it `clipforge`.
- Click "uploading an existing file," drag in every file from this folder, click "Commit."

## 2. Deploy it on Render (free)
- Go to render.com, sign up free (no card needed for free tier).
- Click "New" → "Web Service."
- Connect your GitHub, pick the `clipforge` repo.
- Under "Environment," choose **Docker**.
- Pick the **Free** plan.
- Click "Deploy."

## 3. Wait
- First deploy takes 10–15 minutes (it's downloading the AI model). Normal.
- When it's done, Render gives you a link like `clipforge.onrender.com`. That's your live site.

## 4. Test it
- Open your link, paste a YouTube video **you have rights to use**, click "Make clips."
- First try after being idle can take ~1 minute to wake up — free tier does that.

## What's next
- This version has no sign-up or payments yet — anyone with the link can use it.
- Once it works the way you want, tell Claude and we'll add accounts + the $10/$15 monthly plans with Stripe.
