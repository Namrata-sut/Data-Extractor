# import pandas as pd
# from io import BytesIO
# import xlsxwriter
#
#
# def style_excel(df, output_file=None):
#     """
#     Apply styling to the Excel file: bold header with color, borders, and autosized columns.
#     If output_file is provided, save to disk; otherwise, return BytesIO for download.
#     """
#     # Create a BytesIO object for download or temporary storage
#     output = BytesIO() if output_file is None else None
#     writer = pd.ExcelWriter(output_file or output, engine="xlsxwriter",
#                             engine_kwargs={'options': {'nan_inf_to_errors': True}})
#
#     # Write DataFrame to Excel
#     df.to_excel(writer, index=False, sheet_name="Extract")
#
#     # Get workbook and worksheet
#     workbook = writer.book
#     worksheet = writer.sheets["Extract"]
#
#     # Define formats
#     header_format = workbook.add_format({
#         'bold': True,
#         'bg_color': '#4F81BD',  # Blue header background
#         'font_color': '#FFFFFF',  # White font for header
#         'border': 1,
#         'align': 'center',
#         'valign': 'vcenter'
#     })
#     cell_format = workbook.add_format({
#         'border': 1,
#         'align': 'left',
#         'valign': 'vcenter'
#     })
#
#     # Apply header format
#     for col_num, value in enumerate(df.columns.values):
#         worksheet.write(0, col_num, value, header_format)
#
#     # Apply cell format to all data, handling NaN/INF and strings
#     for row_num in range(1, len(df) + 1):
#         for col_num in range(len(df.columns)):
#             value = df.iloc[row_num - 1, col_num]
#             if pd.isna(value) or value == "N/A":
#                 worksheet.write(row_num, col_num, "N/A", cell_format)
#             else:
#                 worksheet.write(row_num, col_num, value, cell_format)
#
#     # Autosize columns
#     for col_num, column in enumerate(df.columns):
#         max_length = max(
#             df[column].astype(str).map(len).max(),  # Max length of data
#             len(str(column))  # Length of header
#         )
#         worksheet.set_column(col_num, col_num, max_length * 1.2)  # Add padding
#
#     # Keep Policy Number as text
#     if "Policy Number" in df.columns:
#         text_fmt = workbook.add_format({'num_format': '@', 'border': 1})
#         col_idx = df.columns.get_loc("Policy Number")
#         worksheet.set_column(col_idx, col_idx, None, text_fmt)
#
#     # Close writer and return
#     writer.close()
#     if output_file is None:
#         return output.getvalue()
#     return None


import pandas as pd
from io import BytesIO
import xlsxwriter


def style_excel(df, output_file=None):
    """
    Apply styling to the Excel file: bold header with color, borders, and autosized columns.
    If output_file is provided, save to disk; otherwise, return BytesIO for download.
    """
    # Create a BytesIO object for download or temporary storage
    output = BytesIO() if output_file is None else None
    writer = pd.ExcelWriter(output_file or output, engine="xlsxwriter",
                            engine_kwargs={'options': {'nan_inf_to_errors': True}})

    # Write DataFrame to Excel
    df.to_excel(writer, index=False, sheet_name="Extract")

    # Get workbook and worksheet
    workbook = writer.book
    worksheet = writer.sheets["Extract"]

    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4F81BD',  # Blue header background
        'font_color': '#FFFFFF',  # White font for header
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })
    text_format = workbook.add_format({
        'num_format': '@',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })

    # Apply header format
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)

    # Apply cell format to all data, handling NaN/INF and strings
    for row_num in range(1, len(df) + 1):
        for col_num in range(len(df.columns)):
            value = df.iloc[row_num - 1, col_num]
            if df.columns[col_num] == "Policy Number":
                worksheet.write(row_num, col_num, str(value) if not pd.isna(value) else "N/A", text_format)
            elif pd.isna(value) or value == "N/A":
                worksheet.write(row_num, col_num, "N/A", cell_format)
            else:
                worksheet.write(row_num, col_num, value, cell_format)

    # Autosize columns
    for col_num, column in enumerate(df.columns):
        max_length = max(
            df[column].astype(str).map(len).max(),  # Max length of data
            len(str(column))  # Length of header
        )
        worksheet.set_column(col_num, col_num, max_length * 1.2)  # Add padding

    # Close writer and return
    writer.close()
    if output_file is None:
        return output.getvalue()
    return None