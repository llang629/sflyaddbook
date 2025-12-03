#!/usr/bin/env python3
"""Loads address book CSV into Google Sheets."""
# see https://docs.gspread.org/en/latest/user-guide.html
import gspread
import pandas

pandas.options.mode.copy_on_write = True
# see https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html
# #returning-a-view-versus-a-copy

# input from main program default output
INPUT_FILE = "shutterfly_address_book.csv"
# manual prep: create Google Sheet with this name, share with service account
GOOGLE_SHEET = "sflyaddbook"


def str2list(groups_string):
    """Parse text list of groups into data structure."""
    groups_list = []
    for grp in groups_string.split(','):
        grp = grp.strip().strip('[').strip(']').strip("'")
        groups_list.append(grp)
    return groups_list


print("Reading addresses from CSV file", INPUT_FILE)
df = pandas.read_csv(INPUT_FILE, dtype=str)
# assemble list of all Shutterfly address book groups
groups_set = set()
for groups in df['groups']:
    groups_set.update(str2list(groups))

print("Writing addresses to Google sheet", GOOGLE_SHEET)
# authenticate as described in gspread documentation
gc = gspread.service_account()
sh = gc.open(GOOGLE_SHEET)
# delete all existing worksheets, leaving dummy (one worksheet required)
try:
    dummy = sh.add_worksheet(title='dummy', rows=1, cols=1)
except gspread.exceptions.APIError:
    dummy = sh.worksheet('dummy')
worksheet_list = sh.worksheets()
for worksheet in worksheet_list:
    if worksheet.title == 'dummy':
        continue
    sh.del_worksheet(worksheet)

# for each group, create a worksheet
# addresses in multiple groups will appear in multiple worksheets
for group in sorted(groups_set):
    if group == '':
        search_str = r'\[]'
        title_str = "<No Group>"
    else:
        search_str = group
        title_str = group
    print("Adding worksheet for group", title_str)
    group_df = df[df['groups'].str.contains(search_str, na=False)]
    group_df.fillna('', inplace=True)
    num_rows, num_cols = df.shape
    worksheet = sh.add_worksheet(title=title_str, rows=num_rows, cols=num_cols)
    worksheet.update([group_df.columns.values.tolist()] +
                     group_df.values.tolist())

sh.del_worksheet(dummy)
