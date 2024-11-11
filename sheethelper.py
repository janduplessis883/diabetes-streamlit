import os
import pandas as pd
import gspread
from google.oauth2 import service_account


secret_path = os.getenv("SECRET_PATH")


class SheetHelper:
    """
    A helper class to interact with Google Sheets using the gspread library.
    """

    def __init__(self, sheet_url=None, sheet_id=0, secret_file_path=secret_path):
        """
        Initializes the SheetHelper instance and authenticates with the Google Sheets API.

        Parameters:
        - sheet_url (str): The URL of the Google Sheet.
        - sheet_id (int): The index of the worksheet to interact with (default is 0).
        - secret_file_path (str): The file path to the Google service account credentials.
        """
        self.sheet_instance = self.authenticate(sheet_url, sheet_id, secret_file_path)

    def authenticate(self, sheet_url, sheet_id, secret_file_path):
        """
        Authenticates with the Google Sheets API using service account credentials and returns a worksheet instance.

        Parameters:
        - sheet_url (str): The URL of the Google Sheet.
        - sheet_id (int): The index of the worksheet to interact with.
        - secret_file_path (str): The file path to the Google service account credentials.

        Returns:
        - gspread.models.Worksheet: The authenticated worksheet instance.
        """
        credentials = service_account.Credentials.from_service_account_file(
            secret_file_path
        )
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = credentials.with_scopes(scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url)
        return sheet.get_worksheet(sheet_id)

    def append_row(self, row_list):
        """
        Appends a new row to the worksheet.

        Parameters:
        - row_list (list): A list containing the data to be appended as a new row.
        """
        self.sheet_instance.append_row(row_list)
        return "Wrote to Gsheet."

    def get_last_row_index(self):
        """
        Retrieves the index of the last row with data in the worksheet.

        Returns:
        - int: The index of the last row with data.
        """
        return len(self.sheet_instance.get_all_records())

    def update_cell(self, row, col, value):
        """
        Updates a specific cell in the worksheet with a new value.

        Parameters:
        - row (int): The row number of the cell to be updated.
        - col (int): The column number of the cell to be updated.
        - value: The new value to set in the cell.
        """
        self.sheet_instance.update_cell(row, col, value)

    def gsheet_to_df(self, num_rows=None) -> pd.DataFrame:
        """
        Converts the Google Sheet data into a pandas DataFrame with an optional
        parameter to limit the number of rows.

        Parameters:
        - num_rows (int, optional): The number of rows to return from the sheet.
                                    If None, all rows are returned.

        Returns:
        - pd.DataFrame: A DataFrame containing the data from the Google Sheet.
        """
        records = self.sheet_instance.get_all_records()

        # Limit the number of rows if num_rows is specified
        if num_rows is not None:
            records = records[:num_rows]

        return pd.DataFrame.from_dict(records)


    def get_unloaded_emails(self) -> pd.DataFrame:
        """
        Retrieves emails from the Google Sheet that have not been loaded into Chromedb.

        Returns:
        - pd.DataFrame: A DataFrame containing the unloaded emails.
        """
        records = self.sheet_instance.get_all_records()
        df = pd.DataFrame.from_dict(records)

        # Assuming 'Status' is the column indicating if the email is loaded
        unloaded_emails = df[df['Status'] != 'Loaded']
        return unloaded_emails

    def mark_emails_as_loaded(self, email_ids):
        """
        Marks the specified emails as loaded in the Google Sheet by setting 'chroma_status' to 1.

        Parameters:
        - email_ids (list): A list of email identifiers to mark as loaded.
        """
        # Fetch all records to find the rows and update them
        records = self.sheet_instance.get_all_records()

        # Determine the index of 'chroma_status' and 'Email' columns
        header = records[0].keys()
        chroma_status_col = list(header).index('chroma_status') + 1  # gspread is 1-indexed
        email_col = list(header).index('Email') + 1  # assuming 'Email' is the column with the identifier

        for i, record in enumerate(records):
            if record['Email'] in email_ids:
                # Update the 'chroma_status' column to 1 for this email
                self.update_cell(i + 2, chroma_status_col, 1)  # '+2' because records start from index 0 and Google Sheets rows start from 1 (excluding header)
