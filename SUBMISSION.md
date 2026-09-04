# Submission Checklist — HKU AI Agent Technical Test

**Deadline:** 11:59 pm 11 Sep 2026 (HKT)
**To:** junnaifj@hku.hk
**Subject:** 【HKU AI Agent Technical Test】Yule Cai_Universiti Utara Malaysia

## Email Template

```
Subject: 【HKU AI Agent Technical Test】Yule Cai_Universiti Utara Malaysia

Dear Jia,

Thank you for the opportunity. I confirm my submission for the HKU AI Agent Technical Test.

Github: https://github.com/<your-username>/BIMGuard
Video: https://<youtube-or-drive-link>  (<3min walkthrough)
CV: attached one-page PDF (GPA listed for UUM)

Prototype: BIMGuard — AI-Native IFC Compliance Agent
- Stack: Python + FastAPI + IfcOpenShell (fallback parser) + React/Three.js + LLM tool-router
- Rule 1: Exit door width vs HK FS Code 2011 Table B2 (750/850mm)
- Rule 2: Structural/MEP clash via BVH + AABB
- Highlights: deterministic engine → LLM explanation, 3D locate, Ask BIMGuard chat

The repo is runnable with one command: ./run.sh  → http://localhost:8000
Sample IFC: sample-ifc/BIMGuard_Demo.ifc (D-102 fail + B-017×P-042 clash)

Please let me know if any additional info is needed.

Best regards,
Yule Cai
Universiti Utara Malaysia
```

## Deliverables

1. **GitHub repo** must contain:
   - [x] `backend/` (FastAPI + rules + agent)
   - [x] `frontend/` (React + Three.js + static fallback)
   - [x] `prompts/system.md` + `prompts/tools.json` (versioned prompts)
   - [x] `sample-ifc/BIMGuard_Demo.ifc`
   - [x] `README.md` with architecture + quick start
   - [x] `run.sh`

2. **Video** (<3min):
   - Upload to YouTube (unlisted) or Google Drive
   - Follow `VIDEO_SCRIPT.md`

3. **CV** (one-page PDF):
   - Must state GPA for each degree (undergrad + postgrad if any)
   - Export to PDF, attach to email + add to repo as `CV_Yule_Cai.pdf` (optional)

## Pre-send Checks

- [ ] `python3 backend/test_api.py` passes
- [ ] `./run.sh` → http://localhost:8000/ loads static demo
- [ ] Upload demo IFC → score/issues/chat work (curl or UI)
- [ ] `git push` and repo is public
- [ ] Video link is accessible without login
