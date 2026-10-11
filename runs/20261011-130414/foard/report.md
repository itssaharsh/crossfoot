# Crossfoot audit: Foard County, run 20261011-130414

The published spreadsheet was copied from a scanned canvass. This audit compares the two. What it finds are transcription slips in a volunteer dataset; the county's scan is the source. Each finding is proved with the totals printed on the scan itself. No finding has been confirmed by a person.

- Scan: https://raw.githubusercontent.com/openelections/openelections-sources-tx/master/2024/general/2024%20Foard%20County%2C%20TX%20precinct-level%20results.pdf
- Published file: https://raw.githubusercontent.com/openelections/openelections-data-tx/master/2024/counties/20241105__tx__general__foard__precinct.csv

## Counts

2 findings in 2 groups; 0 values changed in the corrected file.

| kind | findings |
|---|---|
| extra_row | 2 |

| status | findings |
|---|---|
| cannot_verify | 2 |

## Printed sums, checked against the published file and the corrected file

Printed sums in all: 700 printed sums (row totals, small totals, grand totals). Recomputed with the published file's values in place of the scan's (matched rows only): 700 hold. Recomputed with the corrected file's values: 700 hold. Rows whose votes differ from their three parts: 0 in the published file, 0 in the corrected file.

No sum fails with the corrected file's values.

## What the printed sums cannot see

In this layout the only sum printed for a value is its row's own: total = absentee + early voting + election day. Where a page prints a contest total ("Total Votes Cast", "Cast Votes"), the candidates' figures in a column also add to it; that is a second sum on the value. Second sum in this county: yes (74 of 74 contests print a contest total).

What one sum cannot see: two numbers of one row that are both wrong and cancel out are not detected. And when a published row differs from the scan's row in two or more values but still adds up to its own total, with no contest total over it, no printed total can tell the two rows apart; such a finding is cannot_verify, nothing is corrected, and the scan's row is read once more so the finding can say whether two readings of the scan agree.

## Look at these first

None: no single-value re-read disagreed with the ledger.

## Could not be corrected as a whole row

None.

Where the scan disagrees with itself, the answer in use is 'cells' (follow the cells as printed and list the printed total as inconsistent); answered by: default, not yet confirmed by a person. It never changes a value; only a printed total that decides can.

## Groups

### g001: extra_row, Jill Stein, precinct Precinct 301

President. Page None, block None. Statuses: cannot_verify 1.

- Precinct Precinct 301, votes: the file has 0, the scan has no row. Status cannot_verify: this file row has no matching row on the scan, so no printed total covers it
  - The scan has no such row.
  - The file shows: votes 0 = absentee 0 + early voting 0 + election day 0.

### g002: extra_row, Jill Stein, precinct Precinct 401

President. Page None, block None. Statuses: cannot_verify 1.

- Precinct Precinct 401, votes: the file has 0, the scan has no row. Status cannot_verify: this file row has no matching row on the scan, so no printed total covers it
  - The scan has no such row.
  - The file shows: votes 0 = absentee 0 + early voting 0 + election day 0.

## What could not be verified, and why

- f001 (group g001), Jill Stein, precinct Precinct 301, votes: cannot_verify. this file row has no matching row on the scan, so no printed total covers it
- f002 (group g002), Jill Stein, precinct Precinct 401, votes: cannot_verify. this file row has no matching row on the scan, so no printed total covers it

Not matched between the scan and the file, so not compared:
- scan block c005: President and Vice President, Vote For 1, Shiva Ayyadurai Crystal Ellis (W)
- scan block c006: President and Vice President, Vote For 1, Jessie Cuellar Wesley Lasley (W)
- scan block c007: President and Vice President, Vote For 1, Claudia De la Cruz Karina Garcia (W)
- scan block c008: President and Vice President, Vote For 1, Cherunda Fox Harlan McVay (W)
- scan block c009: President and Vice President, Vote For 1, Peter Sonski Lauren Onak (W)
- scan block c010: President and Vice President, Vote For 1, Cornel West Melinda Abdullah (W)
- scan block c014: United States Senator, Vote For 1, Tracy Andrus (W)
- scan block c015: United States Senator, Vote For 1, Analisa Roche (W)
- scan block c016: United States Representative, District 13, Vote For 1, Ronny Jackson
- scan block c017: Railroad Commissioner, Vote For 1, Christi Craddick
- scan block c018: Railroad Commissioner, Vote For 1, Katherine Culbert
- scan block c019: Railroad Commissioner, Vote For 1, Hawk Dunlap
- scan block c020: Railroad Commissioner, Vote For 1, Eddie Espinoza
- scan block c021: Railroad Commissioner, Vote For 1, Richard McKibbin (W)
- scan block c022: Justice, Supreme Court, Place 2, Vote For 1, Jimm Blacklock
- scan block c023: Justice, Supreme Court, Place 2, Vote For 1, DaSean Jones
- scan block c024: Justice, Supreme Court, Place 4, Vote For 1, John Devine
- scan block c025: Justice, Supreme Court, Place 4, Vote For 1, Christine Vinh Weems
- scan block c026: Justice, Supreme Court, Place 6, Vote For 1, Jane Bland
- scan block c027: Justice, Supreme Court, Place 6, Vote For 1, Bonnie Lee Goldstein
- scan block c028: Justice, Supreme Court, Place 6, Vote For 1, J. David Roberson
- scan block c029: Presiding Judge, Court of Criminal Appeals, Vote For 1, David J. Schenck
- scan block c030: Presiding Judge, Court of Criminal Appeals, Vote For 1, Holly Taylor
- scan block c031: Judge, Court of Criminal Appeals, Place 7, Vote For 1, Gina Parker
- scan block c032: Judge, Court of Criminal Appeals, Place 7, Vote For 1, Nancy Mulder
- scan block c033: Judge, Court of Criminal Appeals, Place 8, Vote For 1, Lee Finley
- scan block c034: Judge, Court of Criminal Appeals, Place 8, Vote For 1, Chika Anyiam
- scan block c035: Member, State Board of Education, District 15, Vote For 1, Aaron Kinsey
- scan block c036: Member, State Board of Education, District 15, Vote For 1, Morgan Kirkpatrick
- scan block c037: Member, State Board of Education, District 15, Vote For 1, Jack B. Westbrook
- scan block c038: State Representative, District 69, Vote For 1, James B Frank
- scan block c039: State Representative, District 69, Vote For 1, Walter Coppage
- scan block c040: Justice, 7th Court of Appeals District, Place 2, Vote For 1, Judy Parker
- scan block c041: Justice, 7th Court of Appeals District, Place 3, Vote For 1, Alex Yarbrough
- scan block c042: District Attorney, 46th Judicial District, Vote For 1, Jon Whitsitt
- scan block c043: County Attorney, Vote For 1, Karen L. Baylor
- scan block c045: County Commissioner, Precinct No. 1, Vote For 1, Matthew Tamplen
- scan block c046: Constable, Vote For 1, Anthony Hinsley
- scan block c047: President and Vice President, Vote For 1, Jill Stein Rudolph Ware
- scan block c048: County Commissioner, Precinct No. 3, Vote For 1, Doug Johnson
- file: Ballots Cast ,  (4 rows)
- file: President , Over Votes (4 rows)
- file: President , Under Votes (4 rows)
- file: U.S. Senate , Over Votes (4 rows)
- file: U.S. Senate , Under Votes (4 rows)
- file: U.S. House 13, Ronny Jackson (4 rows)
- file: U.S. House 13, Over Votes (4 rows)
- file: U.S. House 13, Under Votes (4 rows)
- file: Railroad Commissioner , Christi Craddick (4 rows)
- file: Railroad Commissioner , Katherine Culbert (4 rows)
- file: Railroad Commissioner , Hawk Dunlap (4 rows)
- file: Railroad Commissioner , Eddie Espinoza (4 rows)
- file: Railroad Commissioner , Over Votes (4 rows)
- file: Railroad Commissioner , Under Votes (4 rows)
- file: Justice, Supreme Court, Place 2 , Jimm Blacklock (4 rows)
- file: Justice, Supreme Court, Place 2 , DaSean Jones (4 rows)
- file: Justice, Supreme Court, Place 2 , Over Votes (4 rows)
- file: Justice, Supreme Court, Place 2 , Under Votes (4 rows)
- file: Justice, Supreme Court, Place 4 , John Devine (4 rows)
- file: Justice, Supreme Court, Place 4 , Christine Vinh Weems (4 rows)
- file: Justice, Supreme Court, Place 4 , Over Votes (4 rows)
- file: Justice, Supreme Court, Place 4 , Under Votes (4 rows)
- file: Justice, Supreme Court, Place 6 , Jane Bland (4 rows)
- file: Justice, Supreme Court, Place 6 , Bonnie Lee Goldstein (4 rows)
- file: Justice, Supreme Court, Place 6 , J. David Roberson (4 rows)
- file: Justice, Supreme Court, Place 6 , Over Votes (4 rows)
- file: Justice, Supreme Court, Place 6 , Under Votes (4 rows)
- file: Presiding Judge, Court of Criminal Appeals , David J. Schenck (4 rows)
- file: Presiding Judge, Court of Criminal Appeals , Holly Taylor (4 rows)
- file: Presiding Judge, Court of Criminal Appeals , Over Votes (4 rows)
- file: Presiding Judge, Court of Criminal Appeals , Under Votes (4 rows)
- file: Judge, Court of Criminal Appeals, Place 7 , Gina Parker (4 rows)
- file: Judge, Court of Criminal Appeals, Place 7 , Nancy Mulder (4 rows)
- file: Judge, Court of Criminal Appeals, Place 7 , Over Votes (4 rows)
- file: Judge, Court of Criminal Appeals, Place 7 , Under Votes (4 rows)
- file: Judge, Court of Criminal Appeals, Place 8 , Lee Finley (4 rows)
- file: Judge, Court of Criminal Appeals, Place 8 , Chika Anyiam (4 rows)
- file: Judge, Court of Criminal Appeals, Place 8 , Over Votes (4 rows)
- file: Judge, Court of Criminal Appeals, Place 8 , Under Votes (4 rows)
- file: Member, State Board of Education 15, Aaron Kinsey (4 rows)
- file: Member, State Board of Education 15, Morgan Kirkpatrick (4 rows)
- file: Member, State Board of Education 15, Jack B. Westbrook (4 rows)
- file: Member, State Board of Education 15, Over Votes (4 rows)
- file: Member, State Board of Education 15, Under Votes (4 rows)
- file: State Representative 69, James B Frank (4 rows)
- file: State Representative 69, Walter Coppage (4 rows)
- file: State Representative 69, Over Votes (4 rows)
- file: State Representative 69, Under Votes (4 rows)
- file: Justice, 7th Court of Appeals District, Place 2 , Judy Parker (4 rows)
- file: Justice, 7th Court of Appeals District, Place 2 , Over Votes (4 rows)
- file: Justice, 7th Court of Appeals District, Place 2 , Under Votes (4 rows)
- file: Justice, 7th Court of Appeals District, Place 3 , Alex Yarbrough (4 rows)
- file: Justice, 7th Court of Appeals District, Place 3 , Over Votes (4 rows)
- file: Justice, 7th Court of Appeals District, Place 3 , Under Votes (4 rows)
- file: District Attorney 46, Jon Whitsitt (4 rows)
- file: District Attorney 46, Over Votes (4 rows)
- file: District Attorney 46, Under Votes (4 rows)
- file: County Attorney , Karen L. Baylor (4 rows)
- file: County Attorney , Over Votes (4 rows)
- file: County Attorney , Under Votes (4 rows)
- file: Sheriff / County Tax Assessor-Collector , Over Votes (4 rows)
- file: Sheriff / County Tax Assessor-Collector , Under Votes (4 rows)
- file: County Commissioner 1, Matthew Tamplen (1 rows)
- file: County Commissioner 1, Over Votes (1 rows)
- file: County Commissioner 1, Under Votes (1 rows)
- file: Constable , Anthony Hinsley (4 rows)
- file: Constable , Over Votes (4 rows)
- file: Constable , Under Votes (4 rows)
- file: County Commissioner 3, Doug Johnson (1 rows)
- file: County Commissioner 3, Over Votes (1 rows)
- file: County Commissioner 3, Under Votes (1 rows)
- rejected pairing, United States Representative, District 13, Vote For 1 = U.S. House: county totals are not close (scan 438, file 549)
- rejected pairing, Railroad Commissioner, Vote For 1 = Railroad Commissioner: county totals are not close (scan 473, file 549)
- rejected pairing, Justice, Supreme Court, Place 2, Vote For 1 = Justice, Supreme Court, Place 2: county totals are not close (scan 475, file 549)
- rejected pairing, Justice, Supreme Court, Place 4, Vote For 1 = Justice, Supreme Court, Place 4: county totals are not close (scan 478, file 549)
- rejected pairing, Justice, Supreme Court, Place 6, Vote For 1 = Justice, Supreme Court, Place 6: county totals are not close (scan 481, file 549)
- rejected pairing, Presiding Judge, Court of Criminal Appeals, Vote For 1 = Presiding Judge, Court of Criminal Appeals: county totals are not close (scan 480, file 549)
- rejected pairing, Judge, Court of Criminal Appeals, Place 7, Vote For 1 = Judge, Court of Criminal Appeals, Place 7: county totals are not close (scan 477, file 549)
- rejected pairing, Judge, Court of Criminal Appeals, Place 8, Vote For 1 = Judge, Court of Criminal Appeals, Place 8: county totals are not close (scan 475, file 549)
- rejected pairing, Member, State Board of Education, District 15, Vote For 1 = Member, State Board of Education: county totals are not close (scan 480, file 549)
- rejected pairing, State Representative, District 69, Vote For 1 = State Representative: county totals are not close (scan 489, file 549)
- rejected pairing, Justice, 7th Court of Appeals District, Place 2, Vote For 1 = Justice, 7th Court of Appeals District, Place 2: county totals are not close (scan 426, file 549)
- rejected pairing, Justice, 7th Court of Appeals District, Place 3, Vote For 1 = Justice, 7th Court of Appeals District, Place 3: county totals are not close (scan 420, file 549)
- rejected pairing, District Attorney, 46th Judicial District, Vote For 1 = District Attorney: county totals are not close (scan 427, file 549)
- rejected pairing, County Attorney, Vote For 1 = County Attorney: county totals are not close (scan 447, file 549)
- rejected pairing, County Commissioner, Precinct No. 1, Vote For 1 = County Commissioner: county totals are not close (scan 102, file 121)
- rejected pairing, Constable, Vote For 1 = Constable: county totals are not close (scan 476, file 549)
- rejected pairing, County Commissioner, Precinct No. 3, Vote For 1 = County Commissioner: county totals are not close (scan 104, file 119)
- rejected pairing, Ronny Jackson = Ronny Jackson: their contests are not paired
- rejected pairing, Christi Craddick = Christi Craddick: their contests are not paired
- rejected pairing, Katherine Culbert = Katherine Culbert: their contests are not paired
- rejected pairing, Hawk Dunlap = Hawk Dunlap: their contests are not paired
- rejected pairing, Eddie Espinoza = Eddie Espinoza: their contests are not paired
- rejected pairing, Jimm Blacklock = Jimm Blacklock: their contests are not paired
- rejected pairing, DaSean Jones = DaSean Jones: their contests are not paired
- rejected pairing, John Devine = John Devine: their contests are not paired
- rejected pairing, Christine Vinh Weems = Christine Vinh Weems: their contests are not paired
- rejected pairing, Jane Bland = Jane Bland: their contests are not paired
- rejected pairing, Bonnie Lee Goldstein = Bonnie Lee Goldstein: their contests are not paired
- rejected pairing, J. David Roberson = J. David Roberson: their contests are not paired
- rejected pairing, David J. Schenck = David J. Schenck: their contests are not paired
- rejected pairing, Holly Taylor = Holly Taylor: their contests are not paired
- rejected pairing, Gina Parker = Gina Parker: their contests are not paired
- rejected pairing, Nancy Mulder = Nancy Mulder: their contests are not paired
- rejected pairing, Lee Finley = Lee Finley: their contests are not paired
- rejected pairing, Chika Anyiam = Chika Anyiam: their contests are not paired
- rejected pairing, Aaron Kinsey = Aaron Kinsey: their contests are not paired
- rejected pairing, Morgan Kirkpatrick = Morgan Kirkpatrick: their contests are not paired
- rejected pairing, Jack B. Westbrook = Jack B. Westbrook: their contests are not paired
- rejected pairing, James B Frank = James B Frank: their contests are not paired
- rejected pairing, Walter Coppage = Walter Coppage: their contests are not paired
- rejected pairing, Judy Parker = Judy Parker: their contests are not paired
- rejected pairing, Alex Yarbrough = Alex Yarbrough: their contests are not paired
- rejected pairing, Jon Whitsitt = Jon Whitsitt: their contests are not paired
- rejected pairing, Karen L. Baylor = Karen L. Baylor: their contests are not paired
- rejected pairing, Matthew Tamplen = Matthew Tamplen: their contests are not paired
- rejected pairing, Anthony Hinsley = Anthony Hinsley: their contests are not paired
- rejected pairing, Doug Johnson = Doug Johnson: their contests are not paired
