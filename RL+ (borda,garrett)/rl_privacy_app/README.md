# PermiSense – Android App Permission Advisor

A website + API built on the six category notebooks in the parent folder
(`Android_Privacy_RL_<Category>.ipynb`). You give it an app (a Google Play link, typed-in details, or a
test-set example) and it returns:

* **Verdict** – likely malicious or likely safe (privacy score vs the category's validation threshold)
* **Allow / Deny for every requested permission group**, decided by the category's Q-learning agent,
  with a short reason and the Android permissions the group covers
* **Risky permission combinations** (decision-tree interaction rules) still present after the recommendations

The website also lists each category's test-set precision, accuracy and recall. The API response
(`/docs`) contains more detail than the website shows: classifier name, α / β / γ, per-step utility,
permission risk, app risk and Q-values, whether the agent had seen the state in training, unmapped and
uncontrolled permissions.

```
rl_privacy_app/
├── export_models.py      # runs each notebook's code and saves the trained models to models/
├── models/               # <category>.json (config, rules, examples) + <category>.joblib (classifier, text models, Q-table)
├── backend/app/          # FastAPI: main.py (endpoints), model.py (inference), playstore.py (Google Play lookup)
├── backend/tests/        # pytest: API checks + parity with the notebook on real test-set apps
├── frontend/             # React + Vite + Tailwind website
├── Dockerfile            # one container: builds the website and serves it with the API
└── docker-compose.yml
```

## 1. What the model needs for an app

| Input | Used for | From a Play Store link |
|---|---|---|
| Category / genre | picks one of the six models | yes (genre is mapped to a category) |
| Permissions | classifier, interaction rules, RL agent | yes, matched to the dataset's permission labels |
| Description + app name | two text-risk features | yes |
| Package name (+ related apps) | package text-risk feature | package yes, related apps no |
| Rating, number of ratings, price | classifier metadata | yes |

Supported Google Play genres: Education, Books & Reference, Tools, Business, Finance, Productivity,
Libraries & Demo, Entertainment, Video Players & Editors, Music & Audio, Comics, Photography, Social,
Communication, News & Magazines, Travel & Local, Personalization, Lifestyle, Health & Fitness, Sports,
Maps & Navigation, Shopping, Medical, Weather, and all Game genres. For any other genre the website asks
you to choose a category.

## 2. Run it locally

Requirements: Python 3.9, Node 18+.

```bash
cd rl_privacy_app
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

**Export the models** (only once; trains every category exactly as its notebook does – about 1–2 hours in
total, the categories can run in parallel):

```bash
.venv/bin/python export_models.py                  # all six
.venv/bin/python export_models.py education games  # or some of them
```

On macOS, if `import lightgbm` fails with `libomp.dylib`, either `brew install libomp`, or copy the
OpenMP library that ships with scikit-learn:

```bash
cd .venv/lib/python3.9/site-packages
cp sklearn/.dylibs/libomp.dylib lightgbm/lib/
install_name_tool -add_rpath @loader_path lightgbm/lib/lib_lightgbm.dylib
codesign --force --sign - lightgbm/lib/lib_lightgbm.dylib lightgbm/lib/libomp.dylib
```

**Start the API** (terminal 1):

```bash
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

**Start the website in development mode** (terminal 2):

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. (Or run `npm run build` once; the API then serves the website itself at
http://localhost:8000.)

## 3. Test it

**Automated tests** (API, link parsing, permission mapping, and parity with the notebooks):

```bash
.venv/bin/python -m pytest backend/tests -q
```

The parity test runs the real test-set example apps of every category through the API and checks that
the verdict, the allowed permissions and the privacy score match what the notebook produced.

**Manual UI checklist**

1. *Try an example* tab → pick a category → click an app labelled malicious and one labelled benign.
   The verdict, score bar, the four score boxes, the permission table and the risky-combinations card must
   appear. *Meet Sexy People* (Social & Communication) shows several risky combinations.
2. *Enter details* tab → choose a category, select a few permission groups (e.g. Camera, Internet,
   PhoneState, Storage), paste a description → Analyze.
3. *Google Play link* tab → paste e.g. `https://play.google.com/store/apps/details?id=com.duolingo`
   → the app icon, developer and verdict appear. Try a non-Play link: a clear error must appear.
   Apps checked on 17 Nov 2026 (live store data, so results can change as ratings and installs change):
   * Likely safe: `com.whatsapp`, `com.instagram.android`, `com.facebook.katana`, `us.zoom.videomeetings`,
     `com.vedantu.app` (one risky combination: Internet + PhoneState + Storage), `com.spotify.music`
   * Likely malicious: `com.vinsontech.fakecallprank`, `com.vinsontech.fakecallprank.free`,
     `com.jangdev.batterysaver`. These are model flags, not confirmed malware.
4. Resize the browser to phone width: the layout must stay readable.
5. http://localhost:8000/docs → interactive API documentation.

**API examples**

```bash
curl -s localhost:8000/api/health
curl -s -X POST localhost:8000/api/analyze -H 'Content-Type: application/json' \
  -d '{"category":"education","app_name":"Notes","description":"Simple notes app",
       "permission_groups":["Internet","Camera","Storage"],"rating":4.1,"num_ratings":350}'
curl -s -X POST localhost:8000/api/analyze-url -H 'Content-Type: application/json' \
  -d '{"url":"https://play.google.com/store/apps/details?id=com.duolingo"}'
```

## 4. Deploy

The Docker image contains the API, the built website and the models (one service, one URL).

```bash
docker compose up --build          # local check: http://localhost:8000
```

**Render** (simple, free tier available): push `rl_privacy_app/` to a GitHub repository (include the
`models/` folder – use Git LFS if a file is over 100 MB), create a *Web Service* → *Docker*, keep the
default port 8000, deploy. **Railway** or **Fly.io** work the same way with the same Dockerfile.
**Hugging Face Spaces**: create a *Docker* Space, upload the folder, set `app_port: 8000` in the Space
README.

Memory: all six models are loaded on first use of each category. Check the size of `models/` – if the
host's free tier has too little memory, use an instance with at least 1–2 GB.

Optional environment variables: `PORT` (default 8000), `MODEL_DIR`, `FRONTEND_DIST`, `CORS_ORIGINS`
(comma-separated, default `*`).

## 5. Play Store reputation adjustment (links only)

The training data comes from an older Play Store snapshot: no app in it has more than ~1.9M ratings, and
today's widely used apps (WhatsApp, Instagram, Spotify, …) are far outside that range, so the classifier
alone flags most of them. For apps analysed from a Google Play link, `playstore.reputation()` turns store
signals that the dataset does not contain into a trust level between 0 and 0.85:

| Signal | Scaled to 0–1 | Weight |
|---|---|---|
| Installs | 10k → 0, 100M → 1 (log scale) | 0.35 |
| Number of ratings | 1k → 0, 10M → 1 (log scale) | 0.25 |
| Average rating | 3.0 → 0, 4.5 → 1 | 0.20 |
| Years on the store | 0 → 0, 5 years → 1 | 0.10 |
| Privacy policy / developer website | present → 1 | 0.05 + 0.05 |

Every classifier risk is then shrunk towards 0.10: `risk = (1 − trust) × classifier risk + trust × 0.10`
(`model.CategoryModel.analyze`). This adjusted risk feeds the RL state, the rewards and the privacy score.
A new or unknown app has trust close to 0, so its result is the model's own. Manual input and the test-set
examples always use trust = 0, i.e. exactly the notebook. The website does not display the trust level.

## 6. Limitations

* The training dataset uses the **old** Google Play permission labels. Current labels are matched to
  them by rules in `backend/app/playstore.py`; labels with no old counterpart are ignored (the API
  returns them as `unmapped_permissions`). "Read the contents of your shared storage" is mapped to the dataset's
  storage permission. Predictions for today's apps are therefore an estimate.
* Google Play has no official public API. The lookup uses `google-play-scraper`, which can break when
  Google changes its pages or rate-limits the server. The manual form always works.
* The description and the number of ratings are among the strongest features. A manually entered app
  with an empty description or 0 ratings looks like the many unrated malicious apps in the dataset, and
  very popular modern apps (hundreds of millions of ratings, dozens of permissions) are far outside the
  training data, so their verdicts should be read with care.
* CallLogs and ReadPhoneNumbers have no column in the dataset, so the models never request them.
* When the RL agent meets a state it never saw in training it uses the notebook's default action
  (allow); the API marks these steps with `learned_state: false`.
