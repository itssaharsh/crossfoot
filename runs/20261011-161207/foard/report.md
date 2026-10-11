# Crossfoot audit: Foard County, run 20261011-161207

The published spreadsheet was copied from a scanned canvass. This audit compares the two. What it finds are transcription slips in a volunteer dataset; the county's scan is the source. Each finding is proved with the totals printed on the scan itself. No finding has been confirmed by a person.

- Scan: https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/2024%20Foard%20County%2C%20TX%20precinct-level%20results.pdf
- Published file: https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/20241105__tx__general__foard__precinct.csv

## Counts

0 findings in 0 groups; 0 values changed in the corrected file.

| kind | findings |
|---|---|
| none | 0 |

| status | findings |
|---|---|
| none | 0 |

## Coverage

The published file has 298 rows; 294 of 298 were compared with the scan.
Not compared:

- Ballots Cast: 4 rows. The contest was not paired with a contest on the scan.

## Printed sums, checked against the published file and the corrected file

Printed sums in all: 700 printed sums (row totals, small totals, grand totals). Recomputed with the published file's values in place of the scan's (matched rows only): 700 hold. Recomputed with the corrected file's values: 700 hold. Rows whose votes differ from their three parts: 0 in the published file, 0 in the corrected file.

No sum fails with the corrected file's values.

## What the printed sums cannot see

In this layout the only sum printed for a value is its row's own: total = absentee + early voting + election day. Where a page prints a contest total ("Total Votes Cast", "Cast Votes"), the candidates' figures in a column also add to it; that is a second sum on the value. Second sum in this county: yes (74 of 74 contests print a contest total).

Where a contest also prints a write-in total with rows that break it down, those rows add to it; and where the precinct's Statistics block prints its ballots cast, the contest total plus overvotes plus undervotes adds to it. 

What one sum cannot see: two numbers of one row that are both wrong and cancel out are not detected. And when a published row differs from the scan's row in two or more values but still adds up to its own total, with no contest total over it, no printed total can tell the two rows apart; such a finding is cannot_verify, nothing is corrected, and the scan's row is read once more so the finding can say whether two readings of the scan agree.

## Look at these first

None: no single-value re-read disagreed with the ledger.

## Could not be corrected as a whole row

None.

Where the scan disagrees with itself, the answer in use is 'cells' (follow the cells as printed and list the printed total as inconsistent); answered by: default, not yet confirmed by a person. It never changes a value; only a printed total that decides can.

## Groups

## What could not be verified, and why

Every finding is settled by a printed total.


Not matched between the scan and the file, so not compared:
- scan block c005: President and Vice President, Vote For 1, Shiva Ayyadurai Crystal Ellis (W)
- scan block c006: President and Vice President, Vote For 1, Jessie Cuellar Wesley Lasley (W)
- scan block c007: President and Vice President, Vote For 1, Claudia De la Cruz Karina Garcia (W)
- scan block c008: President and Vice President, Vote For 1, Cherunda Fox Harlan McVay (W)
- scan block c009: President and Vice President, Vote For 1, Peter Sonski Lauren Onak (W)
- scan block c010: President and Vice President, Vote For 1, Cornel West Melinda Abdullah (W)
- scan block c016: United States Senator, Vote For 1, Tracy Andrus (W)
- scan block c017: United States Senator, Vote For 1, Analisa Roche (W)
- scan block c027: Railroad Commissioner, Vote For 1, Richard McKibbin (W)
- file: Ballots Cast ,  (4 rows)
