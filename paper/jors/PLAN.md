# Plan: resubmit the labapi paper to JORS

Status: draft plan, opened after the JOSS pre-review decision. Facts below were
checked against the live JORS pages on 2026-09-28; every requirement carries
its source so it can be re-checked before submission.

## 1. Where we are

- JOSS closed [openjournals/joss-reviews#11245](https://github.com/openjournals/joss-reviews/issues/11245)
  on 2026-09-16 with labels `rejected` and `query-scope`. The editors decided
  the submission "is not research software as defined by JOSS", while noting
  that "this does not mean that it is not software that is useful in
  research". Automated checks (licence, AI disclosure) had passed. The decision
  was about scope, not quality.
- The JOSS manuscript lives in `paper/paper.md` and still builds through
  `.github/workflows/draft-pdf.yml` (JOSS draft and bioRxiv preprint jobs).
- Version 1.2.0 is archived on Zenodo (version DOI `10.5281/zenodo.22021367`;
  concept DOI `10.5281/zenodo.19599400`, see #301) and published on PyPI.
- `main` carries 39 commits of fixes since the `v1.2.0` tag, which sits on the
  release line rather than on `main`.

## 2. Why JORS fits

The Journal of Open Research Software (Ubiquity Press) publishes "software
metapapers describing research software with high reuse potential", covering
software "either developed in the course of empirical research or explicitly
designed to enable reproducible research"
([About](https://openresearchsoftware.metajnl.com/about/)). Metapapers "do
not contain research results but rather a concise description of research
software, and where to find it"
([Submissions](https://openresearchsoftware.metajnl.com/about/submissions)).
That is exactly the category JOSS said we fall outside of: useful-in-research
infrastructure rather than research software in JOSS's narrower sense.

JORS has no stated exclusion for API clients or vendor wrappers, and has
published them: GTdownloader, "both an API wrapper and a geographic
information pre-processing helper" for the Twitter API
([jors.443](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.443)),
and pybeepop+, a Python interface wrapping a C++ model
([jors.550](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.550)).

Recent Python-library exemplars in the current format: GravDyn
([jors.743](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.743),
Aug 2026) and AgroEcoMetrics
([jors.659](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.659),
Aug 2026).

## 3. What JORS requires

### Manuscript structure (fixed template)

From the official Word template (v0.2) and matching LaTeX class, both
downloadable from the submission page:

1. **Overview**: Title; Paper Authors; Paper Author Roles and Affiliations;
   Abstract (about 100 words, understandable by a non-expert); Keywords;
   Introduction (must include "a short comparison with software that
   implements similar functionality"); Implementation and architecture;
   Quality control (level of testing, and "examples of running the software
   with sample input and output data").
2. **Availability**: Operating system (with minimum version); Programming
   language (with minimum version); Additional system requirements;
   Dependencies; List of contributors (optional); Software location, with an
   **Archive** block (Name, Persistent identifier, Licence, Publisher, Version
   published, Date published) and a **Code repository** block (Name,
   Identifier, Licence, Date published); Language.
3. **Reuse potential**: "must include details of what support mechanisms are
   in place".
4. End matter: Acknowledgements (optional); Funding statement (optional);
   Competing interests (required; if none, the fixed sentence "The authors
   declare that they have no competing interests."); References.

References use the Vancouver numbered system
([Submissions](https://openresearchsoftware.metajnl.com/about/submissions)).
The template text says Harvard; the web page wins. No word limit is stated
for metapapers.

### Software requirements and reviewer checklist

From the [editorial policies](https://openresearchsoftware.metajnl.com/about/editorialpolicies)
and [Submissions](https://openresearchsoftware.metajnl.com/about/submissions):

- Deposited in a repository under an open licence (OSI-approved or CC0), with
  a persistent identifier for the Archive entry. Zenodo (DOI) and GitHub are
  both on the recommended list.
- Public repository so reviewers can find it; licence file included.
- Reviewers are asked: is sample input and output data provided; is the code
  documented for building, deploying and running; does it run on the
  specified systems; is it obvious what the support mechanisms are; does the
  Quality Control section explain trustworthiness.

### Submission mechanics

- Submit through the OJS wizard at
  `https://account.openresearchsoftware.metajnl.com/index.php/up-j-jors/submission/wizard`.
- Accepted formats: `.docx`, or LaTeX source plus PDF. Figures at 150 dpi or
  better.
- Cover letter should suggest five potential reviewers.
- Review is single-anonymous (reviewers know the authors), so the manuscript
  is not anonymised. Decisions are accept / minor / major / reject; JORS
  expects metapapers to be publishable "after one or two rounds".
- APC: £824 for metapapers plus tax, charged on acceptance. A discount or full
  waiver can be requested, but only in the cover letter at submission.
  Institutional agreements give a 10% discount.
- ORCID is strongly recommended, not mandatory. Authorship follows ICMJE.
- AI use: JORS follows the Ubiquity Press AI policy (Nov 2025). Any use beyond
  copyediting must be declared in the manuscript; AI cannot be an author. The
  policy page could not be fetched directly and should be re-read before
  submission.

## 4. Mapping the JOSS paper onto the JORS template

| JOSS section (`paper/paper.md`) | JORS destination | Work needed |
|---|---|---|
| Summary | Abstract | Cut to about 100 words for a non-expert reader. |
| Statement of need | Introduction | Keep; merge in the comparison below. |
| State of the field (table) | Introduction, comparison paragraph | Required by JORS; keep the table, refresh the "checked" date. |
| Software design + Fig. 1 | Implementation and architecture | Mostly reusable. Drop `\autoref`; use plain figure numbers. |
| Example workflow + Fig. 2 | Quality control (sample run) and Reuse potential | JORS wants sample input and output data, not just prose. Point at `examples/csv_table/sample_data.csv` and `examples/json_sync/sample_data`, or add a `paper/jors/sample/` with the QC JSON used in the figures. |
| Research impact statement | Reuse potential | Rewrite around reuse: who else can use it, how to extend it, and the support mechanisms (issue tracker, contributing guide, release cadence, maintainer). |
| Availability | Availability (structured fields) | Fill every field; see skeleton. |
| Author contributions | Paper Author Roles and Affiliations | Fold the CRediT roles into the header block. |
| AI usage disclosure | Dedicated statement before Acknowledgements | Keep; matches the Ubiquity policy. |
| Acknowledgements | Acknowledgements + Funding statement | Split the NIH disclaimer from the two funding lines (NIMH ZICMH002960, NCI contract 75N91019D00024). |
| (none) | Competing interests | New, required. Confirm wording with all authors. |
| References | References, Vancouver numbered | Reuse `paper/paper.bib`; render with a Vancouver CSL. |

The skeleton at `paper/jors/paper.md` applies this mapping and marks every
open item with `TODO`.

## 5. Task list

Ordered so decisions come first and nothing is written twice.

### A. Decisions (authors)

- [ ] Confirm JORS as the venue and accept the APC exposure (£824 plus tax on
      acceptance). Decide whether to request a waiver or discount in the cover
      letter, and check whether NIH Library or NIMH holds a Ubiquity Press or
      JISC-style agreement.
- [ ] Choose the version the paper describes: 1.2.0 as archived, or a 1.2.x
      patch release that includes the fixes on `main` since the tag. The
      Archive block must name one version and date; the paper text and the
      Zenodo version DOI must agree with it.
- [ ] Decide whether to post the bioRxiv preprint before or after JORS
      submission, and check the JORS preprint policy first (not yet verified).
- [ ] Agree the competing-interests sentence and the funding statement with
      all four authors.
- [ ] Pick five suggested reviewers for the cover letter (ELN integration,
      research data management, Python RSE backgrounds).

### B. Software readiness (repository)

- [ ] If a patch release is chosen: cut it with the release process, confirm
      the Zenodo version DOI, then update `codemeta.json` `version`,
      `identifier` and `datePublished`, and the Archive block in the paper.
- [ ] Add a short "Support" section to `README.md` naming the issue tracker,
      the contributing guide, and how questions are handled, so the JORS
      "support mechanisms" question has a visible answer.
- [ ] Make sample input and expected output discoverable from the paper:
      either reference the existing `examples/*/sample_data*` directly, or add
      the QC JSON inputs and the resulting dashboard JSON to
      `paper/jors/sample/`.
- [ ] Confirm the operating-system claim. CI runs on `ubuntu-latest` only
      (`.github/workflows/python_check.yml`), so either state Linux as tested
      and macOS/Windows as supported-but-untested, or add a small OS matrix.
- [ ] Re-check the "State of the field" table entries against the current
      state of each project and update the checked date.

### C. Manuscript

- [ ] Fill every `TODO` in `paper/jors/paper.md`.
- [ ] Write the about-100-word abstract and choose keywords.
- [ ] Expand Quality control: unit tests with `MockClient`, opt-in live
      integration tests, CI on Python 3.10 to 3.14, Ruff, pyright, docs
      build; then the sample run with input and output.
- [ ] Rewrite Reuse potential with explicit support mechanisms.
- [ ] Export `figures/object-model.svg` to a 300 dpi PNG (or PDF for LaTeX)
      and confirm `figures/cohort-dashboard-example.png` meets 150 dpi at
      print size.
- [ ] Build the manuscript. Suggested command from `paper/jors/`, with a
      Vancouver CSL downloaded from the CSL styles repository:

      ```bash
      pandoc paper.md --citeproc --bibliography ../paper.bib \
        --csl vancouver.csl -o paper.docx
      ```

      Optionally add this as a third job in `draft-pdf.yml` once it builds
      cleanly; it is left out of this PR because pandoc was not available to
      verify it locally.
- [ ] Co-author review of the full draft.
- [ ] Draft the cover letter: scope fit, five reviewers, waiver request if
      chosen, and a one-line note that the work was previously considered and
      declined on scope grounds by JOSS.

### D. Submission and after

- [ ] Create the OJS account and submit `.docx` (or LaTeX plus PDF) with
      figures at 150 dpi or better.
- [ ] Respond to review rounds; keep `paper/jors/paper.md` as the source of
      truth and rebuild the `.docx` from it.
- [ ] On acceptance: add `preferred-citation` to `CITATION.cff`, add
      `referencePublication` to `codemeta.json`, add a paper badge to
      `README.md`, and link the article DOI from the Zenodo record.
- [ ] Decide the fate of the JOSS draft job in `draft-pdf.yml` (retire it,
      keep the preprint job).

## 6. Metadata changes made in this PR

- `codemeta.json`: added `softwareRequirements`, `downloadUrl`,
  `releaseNotes`, and `funding`/`funder`, which map onto the JORS
  Dependencies and Funding statement fields.
- `.zenodo.json`: aligned the description, keywords, and affiliations with
  `CITATION.cff` so the next Zenodo deposit matches the paper.
- `CITATION.cff`: unchanged. Its concept DOI is intentional (#301);
  `preferred-citation` is added only once the article exists.
