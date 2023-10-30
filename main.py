from bs4 import BeautifulSoup
from urllib.request import urlopen
from sqlalchemy import create_engine
import pandas as pd
import os
import dotenv
dotenv.load_dotenv()
import traceback




try:

    site_praticagem=os.getenv("SITE_PRATICAGEM")


    with urlopen(site_praticagem) as response:
        soup = BeautifulSoup(response, 'html.parser')

        start_point = soup.find('span', string='PORTO DO AÇU - T1')
        table_ship = start_point.parent.parent.parent.parent.parent.find_all('table')[2]
        barra = start_point.parent.find('div').find('div').get_text(strip=True)


        data = []
        header= [cell.get_text(strip=True) for cell in table_ship.find_all('th')]

        header.append(header[len(header)-1])

        for row in table_ship.find_all('tr'):
            row_data = [cell.get_text(strip=True) for cell in row.find_all('td')]
            data.append(row_data)



    # Create a Pandas DataFrame from the extracted data
    df = pd.DataFrame(data)

    # Print the DataFrame
    # print(barra)

    df.columns = header
    df.dropna(subset=["POB"],inplace=True)



    df["Barra"] = barra

    df = df.loc[:,~df.columns.duplicated()]

    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_database = os.getenv("DB_DATABASE")
    db_host = os.getenv("DB_HOST")
    table_name = os.getenv("DB_TABLE")


    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}/{db_database}"
    
    engine = create_engine(db_url)


    df.to_sql(table_name, engine, if_exists='replace', index=False)
    engine.dispose()



except Exception as e:
    print(e)
    traceback.print_exc()