# Individual contribution submission guide

Assessment 3 allocates 15 marks to the group technical presentation and 15 to the Individual Work and Contribution Summary. Prepare one PDF containing exactly two pages per student, with minimum font size 10. This is a guide, not a completed personal submission.

## Page 1: actual project work

Include student name and ID, responsibilities and completed work since Assessment 2, clickable evidence links, and a short planned-work statement before Assessment 4. Describe a concrete result, the work you performed, the challenge you resolved and how you verified it. Connect each responsibility to evidence that a marker can inspect.

Use the [project repository](https://github.com/xhhetri/Data_Practice_Project), actual commit/PR links, Jira or an equivalent task record, and test/demo evidence. A commit proves a recorded change; it does not by itself prove all team responsibilities or establish the Assessment 2 date boundary.

| Claim | Suitable evidence | What to explain |
|---|---|---|
| Data parsing and alignment | Commit/PR touching Silver/Gold; historical source table; focused test | Units, dates, source boundaries and the defect prevented |
| Forecast experiment | Model commit, fold dates, generated evaluation report | Baseline choice, selection/holdout separation, state-level errors and limitations |
| User workflow | UI/shared-briefing commit, exported briefing, genuine pilot observation | Who completes which task and the observed improvement or remaining failure |
| Reliability | Pipeline/DB/CI commit and successful test/build evidence | Failure handling, quality gates, matching run identity and reproduction |

The new improvements are currently local on `feature/useful-briefings`. Do not cite a GitHub URL for an unpublished file or claim a remote CI run occurred. Once the team commits and pushes its reviewed work, use the actual resulting URLs. Attribute assistance according to the unit's policy and accurately distinguish personal work, collaboration and generated assistance.

## Page 2: one specified lab screenshot and reflection

Include **one screenshot only** for Lab 2 (week 4), Module 8 Storing and Organizing Data — Lab: Storing and Analyzing Data by Using Amazon Redshift. The screenshot must clearly show the lab name, mark, and completion date and time. Use each student's genuine completed lab evidence; do not substitute another lab, fabricate a mark, or insert multiple screenshots.

Write a brief reflection connecting a specific lesson to actual project work. Examples of relevant topics are analytical table grain, organized storage, SQL joins and aggregation, or loading structured data for analysis. The project's tested default is SQLite, so distinguish applying warehouse concepts from actually deploying this project on Redshift. Do not claim a Redshift deployment without evidence.

## Final checks

Count the pages: exactly 2 × number of students. Check every font is at least 10, each page carries the correct student's details where required, links are clickable and accessible to markers, and each lab screenshot remains legible in the exported PDF. Confirm the contribution time window begins after the team's actual Assessment 2 submission. Keep names and IDs out of public repository material unless intended.
