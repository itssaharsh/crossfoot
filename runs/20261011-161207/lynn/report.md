# Crossfoot audit: Lynn County, run 20261011-161207

The published spreadsheet was copied from a scanned canvass. This audit compares the two. What it finds are transcription slips in a volunteer dataset; the county's scan is the source. Each finding is proved with the totals printed on the scan itself. No finding has been confirmed by a person.

- Scan: https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/2024%20Lynn%20County%2C%20TX%20precinct-level%20results.pdf
- Published file: https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/20241105__tx__general__lynn__precinct.csv

## Counts

47 findings in 22 groups; 47 values changed in the corrected file.

| kind | findings |
|---|---|
| wrong_number | 41 |
| wrong_column | 6 |

| status | findings |
|---|---|
| settled_against_file | 47 |

## Coverage

The published file has 650 rows; 634 of 650 were compared with the scan.
Not compared:

- Registered Voters: 8 rows. The contest was not paired with a contest on the scan.
- School Board New Home ISD: 8 rows. The row repeats a precinct of the same candidate and contest.

## Printed sums, checked against the published file and the corrected file

Printed sums in all: 2115 printed sums (row totals, small totals, grand totals). Recomputed with the published file's values in place of the scan's (matched rows only): 2049 hold. Recomputed with the corrected file's values: 2115 hold. Rows whose votes differ from their three parts: 0 in the published file, 0 in the corrected file.

No sum fails with the corrected file's values.

## What the printed sums cannot see

In this layout the only sum printed for a value is its row's own: total = absentee + early voting + election day. Where a page prints a contest total ("Total Votes Cast", "Cast Votes"), the candidates' figures in a column also add to it; that is a second sum on the value. Second sum in this county: yes (149 of 157 contests print a contest total).

Where a contest also prints a write-in total with rows that break it down, those rows add to it; and where the precinct's Statistics block prints its ballots cast, the contest total plus overvotes plus undervotes adds to it. The ballots-cast equation was not used for 1 contest blocks, because it fails in every printed column on the same side (the contest was not on every ballot of the precinct): page 19, block 4|19.

What one sum cannot see: two numbers of one row that are both wrong and cancel out are not detected. And when a published row differs from the scan's row in two or more values but still adds up to its own total, with no contest total over it, no printed total can tell the two rows apart; such a finding is cannot_verify, nothing is corrected, and the scan's row is read once more so the finding can say whether two readings of the scan agree.

## Look at these first

None: no single-value re-read disagreed with the ledger.

## Could not be corrected as a whole row

None.

Where the scan disagrees with itself, the answer in use is 'cells' (follow the cells as printed and list the printed total as inconsistent); answered by: default, not yet confirmed by a person. It never changes a value; only a printed total that decides can.

## Groups

### g001: wrong_number, Ballots Cast, precinct Precinct 6

Ballots Cast. Page 24, block 6|st. Statuses: settled_against_file 2.

![g001](crops/row-0001.png)

- Precinct Precinct 6, votes: the file has 255, the scan has 256. Status settled_against_file: the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total); the contest total, overvotes and undervotes add to the precinct's ballots cast (total) hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (Ballots Cast - Total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 255 (holds).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 256 (does not hold).
- Precinct Precinct 6, election_day: the file has 67, the scan has 68. Status settled_against_file: the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day); the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day) hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (Ballots Cast - Total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 255 (holds).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 68 (does not hold).

### g002: wrong_column, Donald J. Trump, precinct Precinct 2

President. Page 5, block 2|1. Statuses: settled_against_file 2.

![g002](crops/row-0002.png)

- Precinct Precinct 2, early_voting: the file has 141, the scan has 109. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 255; with the scan's value the cells add to 255 (holds); with the file's value they add to 255 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 127; with the scan's value the cells add to 127 (holds); with the file's value they add to 159 (does not hold).
- Precinct Precinct 2, election_day: the file has 109, the scan has 141. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 255; with the scan's value the cells add to 255 (holds); with the file's value they add to 255 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 175; with the scan's value the cells add to 175 (holds); with the file's value they add to 143 (does not hold).

### g003: wrong_number, Donald J. Trump, precinct Precinct 4

President. Page 15, block 4|1. Statuses: settled_against_file 2.

![g003](crops/row-0003.png)

- Precinct Precinct 4, early_voting: the file has 512, the scan has 517. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 895; with the scan's value the cells add to 895 (holds); with the file's value they add to 895 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 545; with the scan's value the cells add to 545 (holds); with the file's value they add to 540 (does not hold).
- Precinct Precinct 4, election_day: the file has 375, the scan has 370. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 895; with the scan's value the cells add to 895 (holds); with the file's value they add to 895 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 423; with the scan's value the cells add to 423 (holds); with the file's value they add to 428 (does not hold).

### g004: wrong_number, Under Votes, precinct Precinct 6

President. Page 24, block 6|1. Statuses: settled_against_file 2.

![g004](crops/row-0004.png)

- Precinct Precinct 6, votes: the file has 0, the scan has 1. Status settled_against_file: the contest total, overvotes and undervotes add to the precinct's ballots cast (total) hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (Undervotes): printed 1; with the scan's value the cells add to 1 (holds); with the file's value they add to 0 (holds).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (total): printed 256; with the scan's value the cells add to 256 (holds); with the file's value they add to 255 (does not hold).
- Precinct Precinct 6, election_day: the file has 0, the scan has 1. Status settled_against_file: the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day) hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (Undervotes): printed 1; with the scan's value the cells add to 1 (holds); with the file's value they add to 0 (holds).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 68; with the scan's value the cells add to 68 (holds); with the file's value they add to 67 (does not hold).

### g005: wrong_number, Bernard Johnson, precinct Precinct 6

U.S. House, 19. Page 24, block 6|3. Statuses: settled_against_file 2.

![g005](crops/row-0005.png)

- Precinct Precinct 6, votes: the file has 24, the scan has 14. Status settled_against_file: the candidates' total figures add to the contest total's total figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Bernard Johnson): printed 14; with the scan's value the cells add to 14 (holds); with the file's value they add to 24 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 231; with the scan's value the cells add to 231 (holds); with the file's value they add to 241 (does not hold).
- Precinct Precinct 6, election_day: the file has 14, the scan has 4. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Bernard Johnson): printed 14; with the scan's value the cells add to 14 (holds); with the file's value they add to 24 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 60; with the scan's value the cells add to 60 (holds); with the file's value they add to 70 (does not hold).

### g006: wrong_number, Nathan Lewis, precinct Precinct 6

U.S. House, 19. Page 24, block 6|3. Statuses: settled_against_file 4.

![g006](crops/row-0006.png)

- Precinct Precinct 6, votes: the file has 14, the scan has 24. Status settled_against_file: the candidates' total figures add to the contest total's total figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 24; with the scan's value the cells add to 24 (holds); with the file's value they add to 14 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 231; with the scan's value the cells add to 231 (holds); with the file's value they add to 221 (does not hold).
- Precinct Precinct 6, absentee: the file has 2, the scan has 1. Status settled_against_file: the candidates' absentee figures add to the contest total's absentee figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 24; with the scan's value the cells add to 24 (holds); with the file's value they add to 14 (holds).
  - the candidates' absentee figures add to the contest total's absentee figure: printed 3; with the scan's value the cells add to 3 (holds); with the file's value they add to 4 (does not hold).
- Precinct Precinct 6, early_voting: the file has 10, the scan has 13. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 24; with the scan's value the cells add to 24 (holds); with the file's value they add to 14 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 168; with the scan's value the cells add to 168 (holds); with the file's value they add to 165 (does not hold).
- Precinct Precinct 6, election_day: the file has 2, the scan has 10. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 24; with the scan's value the cells add to 24 (holds); with the file's value they add to 14 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 60; with the scan's value the cells add to 60 (holds); with the file's value they add to 52 (does not hold).

### g007: wrong_number, Christi Craddick, precinct Precinct 2

Railroad Commissioner. Page 6, block 2|4. Statuses: settled_against_file 2.

![g007](crops/row-0007.png)

- Precinct Precinct 2, early_voting: the file has 100, the scan has 99. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Christl Craddick): printed 229; with the scan's value the cells add to 229 (holds); with the file's value they add to 229 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 123; with the scan's value the cells add to 123 (holds); with the file's value they add to 124 (does not hold).
- Precinct Precinct 2, election_day: the file has 124, the scan has 125. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Christl Craddick): printed 229; with the scan's value the cells add to 229 (holds); with the file's value they add to 229 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 164; with the scan's value the cells add to 164 (holds); with the file's value they add to 163 (does not hold).

### g008: wrong_number, Christi Craddick, precinct Precinct 5

Railroad Commissioner. Page 21, block 5|4. Statuses: settled_against_file 2.

![g008](crops/row-0008.png)

- Precinct Precinct 5, early_voting: the file has 26, the scan has 27. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Christi Craddick): printed 31; with the scan's value the cells add to 31 (holds); with the file's value they add to 31 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 29; with the scan's value the cells add to 29 (holds); with the file's value they add to 28 (does not hold).
- Precinct Precinct 5, election_day: the file has 5, the scan has 4. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Christi Craddick): printed 31; with the scan's value the cells add to 31 (holds); with the file's value they add to 31 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 6; with the scan's value the cells add to 6 (holds); with the file's value they add to 7 (does not hold).

### g009: wrong_column, Hawk Dunlap, precinct Precinct 5

Railroad Commissioner. Page 21, block 5|4. Statuses: settled_against_file 2.

![g009](crops/row-0009.png)

- Precinct Precinct 5, early_voting: the file has 1, the scan has 0. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Hawk Dunlap): printed 1; with the scan's value the cells add to 1 (holds); with the file's value they add to 1 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 29; with the scan's value the cells add to 29 (holds); with the file's value they add to 30 (does not hold).
- Precinct Precinct 5, election_day: the file has 0, the scan has 1. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Hawk Dunlap): printed 1; with the scan's value the cells add to 1 (holds); with the file's value they add to 1 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 6; with the scan's value the cells add to 6 (holds); with the file's value they add to 5 (does not hold).

### g010: wrong_number, Jimmy Blacklock, precinct Precinct 1

Justice, Supreme Court, 2. Page 2, block 1|5. Statuses: settled_against_file 2.

![g010](crops/row-0010.png)

- Precinct Precinct 1, early_voting: the file has 150, the scan has 155. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Jimmy Blacklock): printed 224; with the scan's value the cells add to 224 (holds); with the file's value they add to 224 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 204; with the scan's value the cells add to 204 (holds); with the file's value they add to 199 (does not hold).
- Precinct Precinct 1, election_day: the file has 67, the scan has 62. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Jimmy Blacklock): printed 224; with the scan's value the cells add to 224 (holds); with the file's value they add to 224 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 96; with the scan's value the cells add to 96 (holds); with the file's value they add to 101 (does not hold).

### g011: wrong_number, Jane Bland, precinct Precinct 1

Justice, Supreme Court, 6. Page 2, block 1|7. Statuses: settled_against_file 2.

![g011](crops/row-0011.png)

- Precinct Precinct 1, early_voting: the file has 153, the scan has 155. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Jane Bland): printed 222; with the scan's value the cells add to 222 (holds); with the file's value they add to 222 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 206; with the scan's value the cells add to 206 (holds); with the file's value they add to 204 (does not hold).
- Precinct Precinct 1, election_day: the file has 63, the scan has 61. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Jane Bland): printed 222; with the scan's value the cells add to 222 (holds); with the file's value they add to 222 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 93; with the scan's value the cells add to 93 (holds); with the file's value they add to 95 (does not hold).

### g012: wrong_number, David J. Schenck, precinct Precinct 2

Presiding Judge, Ct of Crim App. Page 7, block 2|8. Statuses: settled_against_file 2.

![g012](crops/row-0012.png)

- Precinct Precinct 2, early_voting: the file has 104, the scan has 105. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 245; with the scan's value the cells add to 245 (holds); with the file's value they add to 245 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 122; with the scan's value the cells add to 122 (holds); with the file's value they add to 121 (does not hold).
- Precinct Precinct 2, election_day: the file has 136, the scan has 135. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 245; with the scan's value the cells add to 245 (holds); with the file's value they add to 245 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 161; with the scan's value the cells add to 161 (holds); with the file's value they add to 162 (does not hold).

### g013: wrong_number, David J. Schenck, precinct Precinct 4

Presiding Judge, Ct of Crim App. Page 17, block 4|8. Statuses: settled_against_file 2.

![g013](crops/row-0013.png)

- Precinct Precinct 4, early_voting: the file has 511, the scan has 510. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 889; with the scan's value the cells add to 889 (holds); with the file's value they add to 889 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 537; with the scan's value the cells add to 537 (holds); with the file's value they add to 538 (does not hold).
- Precinct Precinct 4, election_day: the file has 370, the scan has 371. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 889; with the scan's value the cells add to 889 (holds); with the file's value they add to 889 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 411; with the scan's value the cells add to 411 (holds); with the file's value they add to 410 (does not hold).

### g014: wrong_number, David J. Schenck, precinct Precinct 9

Presiding Judge, Ct of Crim App. Page 31, block 9|8. Statuses: settled_against_file 2.

![g014](crops/row-0014.png)

- Precinct Precinct 9, early_voting: the file has 32, the scan has 33. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 43; with the scan's value the cells add to 43 (holds); with the file's value they add to 43 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 35; with the scan's value the cells add to 35 (holds); with the file's value they add to 34 (does not hold).
- Precinct Precinct 9, election_day: the file has 10, the scan has 9. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 43; with the scan's value the cells add to 43 (holds); with the file's value they add to 43 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 12; with the scan's value the cells add to 12 (holds); with the file's value they add to 13 (does not hold).

### g015: wrong_number, David J. Schenck, precinct Precinct 12

Presiding Judge, Ct of Crim App. Page 35, block 12|8. Statuses: settled_against_file 2.

![g015](crops/row-0015.png)

- Precinct Precinct 12, early_voting: the file has 185, the scan has 187. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 235; with the scan's value the cells add to 235 (holds); with the file's value they add to 235 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 211; with the scan's value the cells add to 211 (holds); with the file's value they add to 209 (does not hold).
- Precinct Precinct 12, election_day: the file has 45, the scan has 43. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP David J. Schenck): printed 235; with the scan's value the cells add to 235 (holds); with the file's value they add to 235 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 48; with the scan's value the cells add to 48 (holds); with the file's value they add to 50 (does not hold).

### g016: wrong_column, Holly Taylor, precinct Precinct 9

Presiding Judge, Ct of Crim App. Page 31, block 9|8. Statuses: settled_against_file 2.

![g016](crops/row-0016.png)

- Precinct Precinct 9, early_voting: the file has 3, the scan has 2. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Holly Taylor): printed 5; with the scan's value the cells add to 5 (holds); with the file's value they add to 5 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 35; with the scan's value the cells add to 35 (holds); with the file's value they add to 36 (does not hold).
- Precinct Precinct 9, election_day: the file has 2, the scan has 3. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Holly Taylor): printed 5; with the scan's value the cells add to 5 (holds); with the file's value they add to 5 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 12; with the scan's value the cells add to 12 (holds); with the file's value they add to 11 (does not hold).

### g017: wrong_number, Gina Parker, precinct Precinct 4

Judge, Ct of Crim App, 7. Page 17, block 4|9. Statuses: settled_against_file 2.

![g017](crops/row-0017.png)

- Precinct Precinct 4, votes: the file has 885, the scan has 889. Status settled_against_file: the candidates' total figures add to the contest total's total figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Gina Parker): printed 889; with the scan's value the cells add to 889 (holds); with the file's value they add to 885 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 956; with the scan's value the cells add to 956 (holds); with the file's value they add to 952 (does not hold).
- Precinct Precinct 4, election_day: the file has 366, the scan has 370. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Gina Parker): printed 889; with the scan's value the cells add to 889 (holds); with the file's value they add to 885 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 410; with the scan's value the cells add to 410 (holds); with the file's value they add to 406 (does not hold).

### g018: wrong_number, Nancy Mulder, precinct Precinct 4

Judge, Ct of Crim App, 7. Page 17, block 4|9. Statuses: settled_against_file 3.

![g018](crops/row-0018.png)

- Precinct Precinct 4, votes: the file has 71, the scan has 67. Status settled_against_file: the candidates' total figures add to the contest total's total figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Nancy Mulder): printed 67; with the scan's value the cells add to 67 (holds); with the file's value they add to 71 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 956; with the scan's value the cells add to 956 (holds); with the file's value they add to 960 (does not hold).
- Precinct Precinct 4, absentee: the file has 3, the scan has 2. Status settled_against_file: the candidates' absentee figures add to the contest total's absentee figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Nancy Mulder): printed 67; with the scan's value the cells add to 67 (holds); with the file's value they add to 71 (holds).
  - the candidates' absentee figures add to the contest total's absentee figure: printed 10; with the scan's value the cells add to 10 (holds); with the file's value they add to 11 (does not hold).
- Precinct Precinct 4, early_voting: the file has 28, the scan has 25. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Nancy Mulder): printed 67; with the scan's value the cells add to 67 (holds); with the file's value they add to 71 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 536; with the scan's value the cells add to 536 (holds); with the file's value they add to 539 (does not hold).

### g019: wrong_number, Under Votes, precinct Precinct 4

Judge, Ct of Crim App, 7. Page 17, block 4|9. Statuses: settled_against_file 2.

![g019](crops/row-0019.png)

- Precinct Precinct 4, absentee: the file has 0, the scan has 1. Status settled_against_file: the contest total, overvotes and undervotes add to the precinct's ballots cast (absentee) hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (Undervotes): printed 26; with the scan's value the cells add to 26 (holds); with the file's value they add to 26 (holds).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (absentee): printed 11; with the scan's value the cells add to 11 (holds); with the file's value they add to 10 (does not hold).
- Precinct Precinct 4, election_day: the file has 16, the scan has 15. Status settled_against_file: the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day) hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (Undervotes): printed 26; with the scan's value the cells add to 26 (holds); with the file's value they add to 26 (holds).
  - the contest total, overvotes and undervotes add to the precinct's ballots cast (election_day): printed 425; with the scan's value the cells add to 425 (holds); with the file's value they add to 426 (does not hold).

### g020: wrong_number, Lee Finley, precinct Precinct 1

Judge, Ct of Crim App, 8. Page 3, block 1|10. Statuses: settled_against_file 2.

![g020](crops/row-0020.png)

- Precinct Precinct 1, early_voting: the file has 159, the scan has 158. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Lee Finley): printed 228; with the scan's value the cells add to 228 (holds); with the file's value they add to 228 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 205; with the scan's value the cells add to 205 (holds); with the file's value they add to 206 (does not hold).
- Precinct Precinct 1, election_day: the file has 63, the scan has 64. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Lee Finley): printed 228; with the scan's value the cells add to 228 (holds); with the file's value they add to 228 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 93; with the scan's value the cells add to 93 (holds); with the file's value they add to 92 (does not hold).

### g021: wrong_number, Aaron Kinsey, precinct Precinct 2

Member, State BoE, 15. Page 7, block 2|11. Statuses: settled_against_file 2.

![g021](crops/row-0021.png)

- Precinct Precinct 2, early_voting: the file has 100, the scan has 106. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Aaron Kinsey): printed 235; with the scan's value the cells add to 235 (holds); with the file's value they add to 235 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 123; with the scan's value the cells add to 123 (holds); with the file's value they add to 117 (does not hold).
- Precinct Precinct 2, election_day: the file has 130, the scan has 124. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Aaron Kinsey): printed 235; with the scan's value the cells add to 235 (holds); with the file's value they add to 235 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 161; with the scan's value the cells add to 161 (holds); with the file's value they add to 167 (does not hold).

### g022: wrong_number, Aaron Kinsey, precinct Precinct 4

Member, State BoE, 15. Page 17, block 4|11. Statuses: settled_against_file 2.

![g022](crops/row-0022.png)

- Precinct Precinct 4, early_voting: the file has 494, the scan has 490. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Aaron Kinsey): printed 852; with the scan's value the cells add to 852 (holds); with the file's value they add to 852 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 537; with the scan's value the cells add to 537 (holds); with the file's value they add to 541 (does not hold).
- Precinct Precinct 4, election_day: the file has 352, the scan has 356. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Aaron Kinsey): printed 852; with the scan's value the cells add to 852 (holds); with the file's value they add to 852 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 408; with the scan's value the cells add to 408 (holds); with the file's value they add to 404 (does not hold).

## What could not be verified, and why

Every finding is settled by a printed total.


Not matched between the scan and the file, so not compared:
- scan block c007: President/Vice President, Write-In: UnCertified
- scan block c008: President/Vice President, Not Assigned
- scan block c015: US Senator, Write-In: UnCertified
- scan block c016: US Senator, Not Assigned
- scan block c029: Railroad Commissioner, Not Assigned
- scan block c090: School Board New Home ISD, 2 Kevin Bass
- scan block c091: School Board New Home ISD, 3 Kevin Bass
- scan block c093: School Board New Home ISD, 1 Justin Tubb
- scan block c094: School Board New Home ISD, 2 Justin Tubb
- scan block c096: School Board New Home ISD, 1 Martin Gill
- scan block c097: School Board New Home ISD, 2 Martin Gill
- scan block c099: School Board New Home ISD, 1 Shaun Weid
- scan block c100: School Board New Home ISD, 2 Shaun Weid
- file: Registered Voters ,  (8 rows)
