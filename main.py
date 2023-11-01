import os
import traceback
from datetime import datetime
import logging
from urllib.request import urlopen
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
import pandas as pd
import dotenv

dotenv.load_dotenv()

# Define the log file name and log format
log_file = "file.log"
log_format = "%(asctime)s - %(levelname)s - %(message)s"

# Create the log file if it doesn't exist
if not os.path.exists(log_file):
    with open(log_file, "w"):
        pass

# Configure the logging settings
logging.basicConfig(filename=log_file, level=logging.INFO, format=log_format)

# now = datetime.now()
# today_date = datetime.strftime(now, format="%Y-%m-%d")

try:
    site_praticagem = os.getenv("SITE_PRATICAGEM")

    with urlopen(site_praticagem) as response:
        soup = BeautifulSoup(response, "html.parser")

        start_point = soup.find("span", string=f"PORTO DO AÇU - T1")
        table_ship = start_point.parent.parent.parent.parent.parent.find_all("table")[2]
        barra = start_point.parent.find("div").find("div").get_text(strip=True)

        data = []
        header = [cell.get_text(strip=True) for cell in table_ship.find_all("th")]

        header.append(header[len(header) - 1])

        for row in table_ship.find_all("tr"):
            row_data = [cell.get_text(strip=True) for cell in row.find_all("td")]
            data.append(row_data)

    # Create a Pandas DataFrame from the extracted data
    df = pd.DataFrame(data)

    # Print the DataFrame
    # print(barra)

    df.columns = header
    df.dropna(subset=["POB"], inplace=True)

    df["Barra"] = barra

    df = df.loc[:, ~df.columns.duplicated()]

    df["POB"] = "2023/" + df["POB"]

    df["POB"] = pd.to_datetime(df["POB"], format="%Y/%d/%m %H:%M")

    df["CALADO"] = df["CALADO"].str.replace(",", ".", regex=False)
    df["LOA"] = df["LOA"].str.replace(",", ".", regex=False)
    df["BOCA"] = df["BOCA"].str.replace(",", ".", regex=False)
    df["GT"] = df["GT"].str.replace(",", ".", regex=False)
    df["DWT"] = df["DWT"].str.replace(",", ".", regex=False)

    df["CALADO"] = pd.to_numeric(df["CALADO"])
    df["LOA"] = pd.to_numeric(df["LOA"])
    df["BOCA"] = pd.to_numeric(df["BOCA"])
    df["GT"] = pd.to_numeric(df["GT"])
    df["DWT"] = pd.to_numeric(df["DWT"])

    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_database = os.getenv("DB_DATABASE")
    db_host = os.getenv("DB_HOST")
    table_name = os.getenv("DB_TABLE")
    db_endpoint = os.getenv("DB_ENDPOINT")

    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}/{db_database}?sslmode=require&options=endpoint%3D{db_endpoint}"

    engine = create_engine(db_url)

    # Create a connection
    connection = engine.connect()

    # Use a raw SQL DELETE statement to delete all rows from the table
    delete_statement = (
        f"DELETE FROM {table_name}"  # Replace with the name of your table
    )

    # Execute the DELETE statement
    connection.execute(delete_statement)

    # Close the connection
    connection.close()

    df.to_sql(table_name, engine, if_exists="replace", index=False)
    engine.dispose()

    logging.info(f"Executado com sucesso!")


except Exception as e:
    print(e)
    traceback.print_exc()
    logging.error(f"message: {e}")
