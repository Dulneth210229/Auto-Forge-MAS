# AutoForge – Research Project Website

Website for the SLIIT research project **R26-SE-033 – AutoForge: A Checkpointed, Human-in-the-Loop Multi-Agent SDLC Pipeline**.

It's plain HTML, CSS and JavaScript. You don't need a build step, a framework or `npm install`.

## Folder structure

```
website/
├── index.html            Home: abstract, pipeline, key results, team
├── domain.html           Literature survey, research gap, problem, objectives, methodology, technologies
├── milestones.html       Every assessment (dropdown + timeline): date, marks, status, documents
├── documents.html        Project charter, proposal, check lists, paper, final reports
├── presentations.html    Proposal, PP1, PP2 and final slides
├── about.html            Group members, supervisors, project details
├── contact.html          Phone numbers, emails, email form, general email template
├── 404.html              "Page not found" page
├── favicon.svg
├── vercel.json           Vercel settings (clean URLs)
└── assets/
    ├── css/styles.css    All styles (light + dark theme)
    ├── js/data.js        ← THE FILE YOU EDIT (links, photos, dates, marks)
    ├── js/main.js        Site behaviour (search, theme, viewer, dropdown…)
    └── img/              Logo, system diagram, team photos
```

## Common updates (all in `assets/js/data.js`)

### Add a OneDrive link to a document or presentation
1. In OneDrive, right-click the file → **Share** → **Copy link**. Set the link to "Anyone with the link can view".
2. In `data.js`, find the item (for example `id: "pp1-slides"`) and paste the link into `url: ""`.
3. You can also set `date: "..."` if you like.

When a link is empty, the site shows **"Link coming soon"** on its own. When a link is filled in, the site shows **Open in OneDrive**. For SharePoint (university) links and `onedrive.live.com` links, it also shows a **View** button that opens the file inside the page.

If the **View** button doesn't appear, or the preview stays blank (this happens with short `1drv.ms` links), do this: in OneDrive, open the file → **File → Share → Embed** → **Generate**. Copy only the `src="..."` address from the code it gives you, and paste it into the item's `embed: ""` field.

### Replace a mock photo with a real one
1. Put the photo in `assets/img/team/` (a square JPG or WebP, about 600×600 px and under 200 KB).
2. Change `photo:` for that member, for example `photo: "assets/img/team/santhuka.jpg"`.

### Milestone dates and marks
Fill in `date: ""` and `marks: ""` for each milestone. While they are empty, the site shows "To be confirmed". You can set `status:` to `"completed"`, `"in-progress"` or `"upcoming"`.

### Supervisor emails, member links
Fill in `email` for each supervisor, and `links.github` or `links.linkedin` for each member.

## Run it on your computer
Open `index.html` in a browser, or run a small local server from this folder:

```
python -m http.server 8000
```

Then open http://localhost:8000.

## Deploy to Vercel
1. Copy this `website` folder into a new GitHub repository. The files should sit at the root of the repo.
2. On vercel.com: **Add New → Project** → import the repository.
3. Framework preset: **Other**. Leave the build command and output directory empty. Click **Deploy**.
4. Every push to the repository updates the site.

The whole site is well under the university's 20 MB limit.
