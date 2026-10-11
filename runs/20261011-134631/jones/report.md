# Crossfoot audit: Jones County, run 20261011-134631

The published spreadsheet was copied from a scanned canvass. This audit compares the two. What it finds are transcription slips in a volunteer dataset; the county's scan is the source. Each finding is proved with the totals printed on the scan itself. No finding has been confirmed by a person.

- Scan: https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/2024%20Jones%20County%2C%20TX%20precinct-level%20results.pdf
- Published file: https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/20241105__tx__general__jones__precinct.csv

## Counts

26 findings in 13 groups; 18 values changed in the corrected file.

| kind | findings |
|---|---|
| wrong_number | 26 |

| status | findings |
|---|---|
| settled_against_file | 18 |
| cannot_verify | 8 |

## Coverage

The published file has 344 rows; 335 of 344 were compared with the scan.
Not compared:

- Registered Voters: 4 rows. The contest was not paired with a contest on the scan.
- Ballots Cast Blank: 4 rows. The contest was not paired with a contest on the scan.
- Trustee Roby CISD: 1 row. The contest is paired, but this candidate has no block on the scan.

## Printed sums, checked against the published file and the corrected file

Printed sums in all: 758 printed sums (row totals, small totals, grand totals). Recomputed with the published file's values in place of the scan's (matched rows only): 726 hold. Recomputed with the corrected file's values: 738 hold. Rows whose votes differ from their three parts: 0 in the published file, 0 in the corrected file.

20 sums still fail with the corrected file's values:

- page 1, block 1|1: the candidates' total figures add to the contest total's total figure (printed 1206, adds to 1207). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 1, block 1|1: the candidates' election day figures add to the contest total's election day figure (printed 485, adds to 486). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 2, block 1|4: the candidates' total figures add to the contest total's total figure (printed 1153, adds to 1154). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 2, block 1|4: the candidates' absentee figures add to the contest total's absentee figure (printed 48, adds to 49). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 6, block 2|1: the candidates' total figures add to the contest total's total figure (printed 1629, adds to 1536). Why: a value that could not be verified (f001: Donald J. Trump/JD Vance, precinct Precinct 2, votes); a value that could not be verified (f002: Donald J. Trump/JD Vance, precinct Precinct 2, election_day); a value that could not be verified (f005: Kamala D. Harris/Tim Walz, precinct Precinct 2, early_voting); a value that could not be verified (f006: Kamala D. Harris/Tim Walz, precinct Precinct 2, election_day).
- page 6, block 2|1: the candidates' early voting figures add to the contest total's early voting figure (printed 841, adds to 845). Why: a value that could not be verified (f001: Donald J. Trump/JD Vance, precinct Precinct 2, votes); a value that could not be verified (f002: Donald J. Trump/JD Vance, precinct Precinct 2, election_day); a value that could not be verified (f005: Kamala D. Harris/Tim Walz, precinct Precinct 2, early_voting); a value that could not be verified (f006: Kamala D. Harris/Tim Walz, precinct Precinct 2, election_day).
- page 6, block 2|1: the candidates' election day figures add to the contest total's election day figure (printed 721, adds to 624). Why: a value that could not be verified (f001: Donald J. Trump/JD Vance, precinct Precinct 2, votes); a value that could not be verified (f002: Donald J. Trump/JD Vance, precinct Precinct 2, election_day); a value that could not be verified (f005: Kamala D. Harris/Tim Walz, precinct Precinct 2, early_voting); a value that could not be verified (f006: Kamala D. Harris/Tim Walz, precinct Precinct 2, election_day).
- page 11, block 3|1: the candidates' total figures add to the contest total's total figure (printed 2102, adds to 2094). Why: a value that could not be verified (f003: Donald J. Trump/JD Vance, precinct Precinct 3, votes); a value that could not be verified (f004: Donald J. Trump/JD Vance, precinct Precinct 3, election_day).
- page 11, block 3|1: the candidates' election day figures add to the contest total's election day figure (printed 819, adds to 811). Why: a value that could not be verified (f003: Donald J. Trump/JD Vance, precinct Precinct 3, votes); a value that could not be verified (f004: Donald J. Trump/JD Vance, precinct Precinct 3, election_day).
- page 11, block 3|2: the candidates' total figures add to the contest total's total figure (printed 2096, adds to 2097). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 11, block 3|2: the candidates' election day figures add to the contest total's election day figure (printed 812, adds to 813). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 12, block 3|4: the candidates' total figures add to the contest total's total figure (printed 2037, adds to 2039). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 12, block 3|4: the candidates' absentee figures add to the contest total's absentee figure (printed 44, adds to 45). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 12, block 3|4: the candidates' early voting figures add to the contest total's early voting figure (printed 1205, adds to 1206). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 16, block 4|1: the candidates' total figures add to the contest total's total figure (printed 2022, adds to 2025). Why: a value that could not be verified (f007: Kamala D. Harris/Tim Walz, precinct Precinct 4, early_voting); a value that could not be verified (f008: Kamala D. Harris/Tim Walz, precinct Precinct 4, election_day).
- page 16, block 4|1: the candidates' early voting figures add to the contest total's early voting figure (printed 1271, adds to 1282). Why: a value that could not be verified (f007: Kamala D. Harris/Tim Walz, precinct Precinct 4, early_voting); a value that could not be verified (f008: Kamala D. Harris/Tim Walz, precinct Precinct 4, election_day).
- page 16, block 4|1: the candidates' election day figures add to the contest total's election day figure (printed 673, adds to 665). Why: a value that could not be verified (f007: Kamala D. Harris/Tim Walz, precinct Precinct 4, early_voting); a value that could not be verified (f008: Kamala D. Harris/Tim Walz, precinct Precinct 4, election_day).
- page 16, block 4|2: the candidates' total figures add to the contest total's total figure (printed 2009, adds to 2011). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 16, block 4|2: the candidates' early voting figures add to the contest total's early voting figure (printed 1260, adds to 1261). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.
- page 16, block 4|2: the candidates' election day figures add to the contest total's election day figure (printed 671, adds to 672). Why: the scan's own cells and its printed total disagree, and no difference from the file is involved.

## What the printed sums cannot see

In this layout the only sum printed for a value is its row's own: total = absentee + early voting + election day. Where a page prints a contest total ("Total Votes Cast", "Cast Votes"), the candidates' figures in a column also add to it; that is a second sum on the value. Second sum in this county: yes (78 of 82 contests print a contest total).

What one sum cannot see: two numbers of one row that are both wrong and cancel out are not detected. And when a published row differs from the scan's row in two or more values but still adds up to its own total, with no contest total over it, no printed total can tell the two rows apart; such a finding is cannot_verify, nothing is corrected, and the scan's row is read once more so the finding can say whether two readings of the scan agree.

## Look at these first

None: no single-value re-read disagreed with the ledger.

## Could not be corrected as a whole row

None.

Where the scan disagrees with itself, the answer in use is 'cells' (follow the cells as printed and list the printed total as inconsistent); answered by: default, not yet confirmed by a person. It never changes a value; only a printed total that decides can.

## Groups

### g001: wrong_number, Donald J. Trump/JD Vance, precinct Precinct 2

President. Page 6, block 2|1. Statuses: cannot_verify 2.

![g001](crops/row-0001.png)

- Precinct Precinct 2, votes: the file has 1263, the scan has 1363. Status cannot_verify: no printed total decides: the candidates' total figures add to the contest total's total figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 1363; with the scan's value the cells add to 1363 (holds); with the file's value they add to 1263 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 1629; with the scan's value the cells add to 1636 (does not hold); with the file's value they add to 1536 (does not hold).
- Precinct Precinct 2, election_day: the file has 494, the scan has 594. Status cannot_verify: no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 1363; with the scan's value the cells add to 1363 (holds); with the file's value they add to 1263 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 721; with the scan's value the cells add to 726 (does not hold); with the file's value they add to 626 (does not hold).

### g002: wrong_number, Donald J. Trump/JD Vance, precinct Precinct 3

President. Page 11, block 3|1. Statuses: cannot_verify 2.

![g002](crops/row-0002.png)

- Precinct Precinct 3, votes: the file has 1858, the scan has 1868. Status cannot_verify: no printed total decides: the candidates' total figures add to the contest total's total figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 1868; with the scan's value the cells add to 1868 (holds); with the file's value they add to 1858 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 2102; with the scan's value the cells add to 2104 (does not hold); with the file's value they add to 2094 (does not hold).
- Precinct Precinct 3, election_day: the file has 722, the scan has 732. Status cannot_verify: no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (REP Donald J. Trump/JD Vance): printed 1868; with the scan's value the cells add to 1868 (holds); with the file's value they add to 1858 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 819; with the scan's value the cells add to 821 (does not hold); with the file's value they add to 811 (does not hold).

### g003: wrong_number, Kamala D. Harris/Tim Walz, precinct Precinct 2

President. Page 6, block 2|1. Statuses: cannot_verify 2.

![g003](crops/row-0003.png)

- Precinct Precinct 2, early_voting: the file has 112, the scan has 110. Status cannot_verify: no printed total decides: the candidates' early voting figures add to the contest total's early voting figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Kamala D. Harris/Tim Walz): printed 247; with the scan's value the cells add to 247 (holds); with the file's value they add to 247 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 841; with the scan's value the cells add to 843 (does not hold); with the file's value they add to 845 (does not hold).
- Precinct Precinct 2, election_day: the file has 111, the scan has 113. Status cannot_verify: no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Kamala D. Harris/Tim Walz): printed 247; with the scan's value the cells add to 247 (holds); with the file's value they add to 247 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 721; with the scan's value the cells add to 726 (does not hold); with the file's value they add to 724 (does not hold).

### g004: wrong_number, Kamala D. Harris/Tim Walz, precinct Precinct 4

President. Page 16, block 4|1. Statuses: cannot_verify 2.

![g004](crops/row-0004.png)

- Precinct Precinct 4, early_voting: the file has 136, the scan has 126. Status cannot_verify: no printed total decides: the candidates' early voting figures add to the contest total's early voting figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Kamala D. Harris/Tim Walz): printed 229; with the scan's value the cells add to 229 (holds); with the file's value they add to 229 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 1271; with the scan's value the cells add to 1272 (does not hold); with the file's value they add to 1282 (does not hold).
- Precinct Precinct 4, election_day: the file has 72, the scan has 82. Status cannot_verify: no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Kamala D. Harris/Tim Walz): printed 229; with the scan's value the cells add to 229 (holds); with the file's value they add to 229 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 673; with the scan's value the cells add to 675 (does not hold); with the file's value they add to 665 (does not hold).

### g005: wrong_number, Bernard Johnson, precinct Precinct 2

U.S. House, 19. Page 6, block 2|3. Statuses: settled_against_file 2.

![g005](crops/row-0005.png)

- Precinct Precinct 2, votes: the file has 93, the scan has 95. Status settled_against_file: the candidates' total figures add to the contest total's total figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Bernard Johnson): printed 95; with the scan's value the cells add to 95 (holds); with the file's value they add to 93 (holds).
  - the candidates' total figures add to the contest total's total figure: printed 1554; with the scan's value the cells add to 1554 (holds); with the file's value they add to 1552 (does not hold).
- Precinct Precinct 2, election_day: the file has 43, the scan has 45. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Bernard Johnson): printed 95; with the scan's value the cells add to 95 (holds); with the file's value they add to 93 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 677; with the scan's value the cells add to 677 (holds); with the file's value they add to 675 (does not hold).

### g006: wrong_number, Bernard Johnson, precinct Precinct 4

U.S. House, 19. Page 16, block 4|3. Statuses: settled_against_file 2.

![g006](crops/row-0006.png)

- Precinct Precinct 4, absentee: the file has 8, the scan has 5. Status settled_against_file: the candidates' absentee figures add to the contest total's absentee figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Bernard Johnson): printed 96; with the scan's value the cells add to 96 (holds); with the file's value they add to 96 (holds).
  - the candidates' absentee figures add to the contest total's absentee figure: printed 72; with the scan's value the cells add to 72 (holds); with the file's value they add to 75 (does not hold).
- Precinct Precinct 4, election_day: the file has 42, the scan has 45. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Bernard Johnson): printed 96; with the scan's value the cells add to 96 (holds); with the file's value they add to 96 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 660; with the scan's value the cells add to 660 (holds); with the file's value they add to 657 (does not hold).

### g007: wrong_number, Nathan Lewis, precinct Precinct 1

U.S. House, 19. Page 1, block 1|3. Statuses: settled_against_file 2.

![g007](crops/row-0007.png)

- Precinct Precinct 1, early_voting: the file has 42, the scan has 32. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 76; with the scan's value the cells add to 76 (holds); with the file's value they add to 76 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 633; with the scan's value the cells add to 633 (holds); with the file's value they add to 643 (does not hold).
- Precinct Precinct 1, election_day: the file has 27, the scan has 37. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 76; with the scan's value the cells add to 76 (holds); with the file's value they add to 76 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 458; with the scan's value the cells add to 458 (holds); with the file's value they add to 448 (does not hold).

### g008: wrong_number, Nathan Lewis, precinct Precinct 2

U.S. House, 19. Page 6, block 2|3. Statuses: settled_against_file 2.

![g008](crops/row-0008.png)

- Precinct Precinct 2, absentee: the file has 7, the scan has 9. Status settled_against_file: the candidates' absentee figures add to the contest total's absentee figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 104; with the scan's value the cells add to 104 (holds); with the file's value they add to 104 (holds).
  - the candidates' absentee figures add to the contest total's absentee figure: printed 64; with the scan's value the cells add to 64 (holds); with the file's value they add to 62 (does not hold).
- Precinct Precinct 2, election_day: the file has 50, the scan has 48. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 104; with the scan's value the cells add to 104 (holds); with the file's value they add to 104 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 677; with the scan's value the cells add to 677 (holds); with the file's value they add to 679 (does not hold).

### g009: wrong_number, Nathan Lewis, precinct Precinct 4

U.S. House, 19. Page 16, block 4|3. Statuses: settled_against_file 2.

![g009](crops/row-0009.png)

- Precinct Precinct 4, absentee: the file has 6, the scan has 9. Status settled_against_file: the candidates' absentee figures add to the contest total's absentee figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 113; with the scan's value the cells add to 113 (holds); with the file's value they add to 113 (holds).
  - the candidates' absentee figures add to the contest total's absentee figure: printed 72; with the scan's value the cells add to 72 (holds); with the file's value they add to 69 (does not hold).
- Precinct Precinct 4, election_day: the file has 47, the scan has 44. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (IND Nathan Lewis): printed 113; with the scan's value the cells add to 113 (holds); with the file's value they add to 113 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 660; with the scan's value the cells add to 660 (holds); with the file's value they add to 663 (does not hold).

### g010: wrong_number, John Devine, precinct Precinct 1

Justice, Supreme Court, Pl 4. Page 2, block 1|6. Statuses: settled_against_file 2.

![g010](crops/row-0010.png)

- Precinct Precinct 1, early_voting: the file has 550, the scan has 545. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP John Devine): printed 946; with the scan's value the cells add to 946 (holds); with the file's value they add to 946 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 645; with the scan's value the cells add to 645 (holds); with the file's value they add to 650 (does not hold).
- Precinct Precinct 1, election_day: the file has 370, the scan has 375. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (REP John Devine): printed 946; with the scan's value the cells add to 946 (holds); with the file's value they add to 946 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 461; with the scan's value the cells add to 461 (holds); with the file's value they add to 456 (does not hold).

### g011: wrong_number, Holly Taylor, precinct Precinct 1

Presiding Judge, Ct of Crim App. Page 3, block 1|8. Statuses: settled_against_file 2.

![g011](crops/row-0011.png)

- Precinct Precinct 1, early_voting: the file has 91, the scan has 90. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Holly Taylor): printed 201; with the scan's value the cells add to 201 (holds); with the file's value they add to 201 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 642; with the scan's value the cells add to 642 (holds); with the file's value they add to 643 (does not hold).
- Precinct Precinct 1, election_day: the file has 88, the scan has 89. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Holly Taylor): printed 201; with the scan's value the cells add to 201 (holds); with the file's value they add to 201 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 461; with the scan's value the cells add to 461 (holds); with the file's value they add to 460 (does not hold).

### g012: wrong_number, Holly Taylor, precinct Precinct 3

Presiding Judge, Ct of Crim App. Page 13, block 3|8. Statuses: settled_against_file 2.

![g012](crops/row-0012.png)

- Precinct Precinct 3, early_voting: the file has 115, the scan has 120. Status settled_against_file: the candidates' early voting figures add to the contest total's early voting figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Holly Taylor): printed 206; with the scan's value the cells add to 206 (holds); with the file's value they add to 206 (holds).
  - the candidates' early voting figures add to the contest total's early voting figure: printed 1201; with the scan's value the cells add to 1201 (holds); with the file's value they add to 1196 (does not hold).
- Precinct Precinct 3, election_day: the file has 80, the scan has 75. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (DEM Holly Taylor): printed 206; with the scan's value the cells add to 206 (holds); with the file's value they add to 206 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 778; with the scan's value the cells add to 778 (holds); with the file's value they add to 783 (does not hold).

### g013: wrong_number, Jack B. Westbrook, precinct Precinct 3

Member, State BoE, Dist 15. Page 13, block 3|11. Statuses: settled_against_file 2.

![g013](crops/row-0013.png)

- Precinct Precinct 3, absentee: the file has 4, the scan has 3. Status settled_against_file: the candidates' absentee figures add to the contest total's absentee figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Jack B. Westbrook): printed 54; with the scan's value the cells add to 54 (holds); with the file's value they add to 54 (holds).
  - the candidates' absentee figures add to the contest total's absentee figure: printed 44; with the scan's value the cells add to 44 (holds); with the file's value they add to 45 (does not hold).
- Precinct Precinct 3, election_day: the file has 22, the scan has 23. Status settled_against_file: the candidates' election day figures add to the contest total's election day figure hold(s) with the scan's value and fail(s) with the file's, and no printed total holds with the file's value and fails with the scan's Changed in the corrected file.
  - the row's total printed on the scan equals its absentee + early voting + election day (LIB Jack B. Westbrook): printed 54; with the scan's value the cells add to 54 (holds); with the file's value they add to 54 (holds).
  - the candidates' election day figures add to the contest total's election day figure: printed 776; with the scan's value the cells add to 776 (holds); with the file's value they add to 775 (does not hold).

## What could not be verified, and why

- f001 (group g001), Donald J. Trump/JD Vance, precinct Precinct 2, votes: cannot_verify. no printed total decides: the candidates' total figures add to the contest total's total figure give the same answer with either value
- f002 (group g001), Donald J. Trump/JD Vance, precinct Precinct 2, election_day: cannot_verify. no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
- f003 (group g002), Donald J. Trump/JD Vance, precinct Precinct 3, votes: cannot_verify. no printed total decides: the candidates' total figures add to the contest total's total figure give the same answer with either value
- f004 (group g002), Donald J. Trump/JD Vance, precinct Precinct 3, election_day: cannot_verify. no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
- f005 (group g003), Kamala D. Harris/Tim Walz, precinct Precinct 2, early_voting: cannot_verify. no printed total decides: the candidates' early voting figures add to the contest total's early voting figure give the same answer with either value
- f006 (group g003), Kamala D. Harris/Tim Walz, precinct Precinct 2, election_day: cannot_verify. no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
- f007 (group g004), Kamala D. Harris/Tim Walz, precinct Precinct 4, early_voting: cannot_verify. no printed total decides: the candidates' early voting figures add to the contest total's early voting figure give the same answer with either value
- f008 (group g004), Kamala D. Harris/Tim Walz, precinct Precinct 4, election_day: cannot_verify. no printed total decides: the candidates' election day figures add to the contest total's election day figure give the same answer with either value
- The ledger itself: report_contest:11:3|1:election_day ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the election_day column hold: the candidates add to 821, the contest total prints 819
- The ledger itself: report_contest:11:3|1:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 2104, the contest total prints 2102
- The ledger itself: report_contest:11:3|2:election_day ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the election_day column hold: the candidates add to 813, the contest total prints 812
- The ledger itself: report_contest:11:3|2:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 2097, the contest total prints 2096
- The ledger itself: report_contest:12:3|4:absentee ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the absentee column hold: the candidates add to 45, the contest total prints 44
- The ledger itself: report_contest:12:3|4:early ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the early column hold: the candidates add to 1206, the contest total prints 1205
- The ledger itself: report_contest:12:3|4:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 2039, the contest total prints 2037
- The ledger itself: report_contest:16:4|1:early ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the early column hold: the candidates add to 1272, the contest total prints 1271
- The ledger itself: report_contest:16:4|1:election_day ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the election_day column hold: the candidates add to 675, the contest total prints 673
- The ledger itself: report_contest:16:4|1:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 2025, the contest total prints 2022
- The ledger itself: report_contest:16:4|2:early ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the early column hold: the candidates add to 1261, the contest total prints 1260
- The ledger itself: report_contest:16:4|2:election_day ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the election_day column hold: the candidates add to 672, the contest total prints 671
- The ledger itself: report_contest:16:4|2:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 2011, the contest total prints 2009
- The ledger itself: report_contest:1:1|1:election_day ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the election_day column hold: the candidates add to 486, the contest total prints 485
- The ledger itself: report_contest:1:1|1:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 1207, the contest total prints 1206
- The ledger itself: report_contest:2:1|4:absentee ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the absentee column hold: the candidates add to 49, the contest total prints 48
- The ledger itself: report_contest:2:1|4:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 1154, the contest total prints 1153
- The ledger itself: report_contest:6:2|1:early ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the early column hold: the candidates add to 843, the contest total prints 841
- The ledger itself: report_contest:6:2|1:election_day ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the election_day column hold: the candidates add to 726, the contest total prints 721
- The ledger itself: report_contest:6:2|1:total ended cannot_verify. 6 re-read(s) of the rows of this contest did not make the total column hold: the candidates add to 1636, the contest total prints 1629

Not matched between the scan and the file, so not compared:
- scan block c007: President/Vice President, Write-In: Uncertified
- scan block c008: President/Vice President, Write-In: Peter Sonski
- scan block c009: President/Vice President, Not Assigned
- scan block c016: US Senator, Write-In: Uncertified
- scan block c017: US Senator, Not Assigned
- scan block c030: Railroad Commissioner, Write-In: Richard McKibbin
- scan block c031: Railroad Commissioner, Write-In: Uncertified
- scan block c032: Railroad Commissioner, Not Assigned
- scan block c105: Trustee Roby CISD, Danny Carrion
- file: Registered Voters ,  (4 rows)
- file: Ballots Cast Blank ,  (4 rows)
- file: Trustee Roby CISD , Danny Garison (1 rows)
