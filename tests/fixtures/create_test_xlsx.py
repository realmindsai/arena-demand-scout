"""Generate a minimal ABS-format XLSX for testing. Run once."""

import datetime
import openpyxl
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent


def create_sample_projection_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data1"

    # Row 0: Column descriptions (matching real ABS format)
    ages = list(range(0, 6))  # only ages 0-5 for test brevity
    headers = [None]  # Column 0 has no header in row 0
    for sex in ["Male", "Female"]:
        for age in ages:
            headers.append(f"Projected persons ;  Series 29(B) ;  Vic ;  {sex} ;  {age} ;")
    ws.append(headers)

    # Rows 1-8: Metadata rows (simplified)
    ws.append(["Unit"] + ["Number"] * (len(headers) - 1))
    for label in ["Series Type", "Data Type", "Frequency", "Collection Month", "Series Start", "Series End", "No. Obs"]:
        ws.append([label] + [None] * (len(headers) - 1))

    # Row 9: Series ID
    ws.append(["Series ID"] + [f"A{i}" for i in range(len(headers) - 1)])

    # Rows 10+: Data rows (2022-2036 = 15 years)
    for year_offset in range(15):
        year = 2022 + year_offset
        dt = datetime.datetime(year, 6, 1)
        row = [dt]
        for sex in ["Male", "Female"]:
            for age in ages:
                # base 33000 per age/sex, grows 200/year
                row.append(33000 + year_offset * 200 + age * 100)
        ws.append(row)

    wb.save(FIXTURE_DIR / "sample_projection.xlsx")
    print(f"Created {FIXTURE_DIR / 'sample_projection.xlsx'}")


if __name__ == "__main__":
    create_sample_projection_xlsx()
