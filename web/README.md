# Tank Controller Dashboard (Static Site)

This directory contains the static web files for the **Tank Controller Dashboard**.

## Deployment
This folder is ready to be deployed to any static site hosting provider, such as:
- **Render** (Static Site)
- **Vercel**
- **Netlify**
- **GitHub Pages**

## Configuration
The `index.html` file contains the logic to connect to **Firebase Realtime Database**.
Ensure you have updated the `firebaseConfig` section in `index.html` with your own Firebase API Key and Database URL before deploying.

## Setup on Render
1.  Create a new **Static Site** on Render.
2.  Connect this repository.
3.  Set the **Root Directory** to `web`.
4.  Set the **Publish Directory** to `.`.
5.  Deploy!
