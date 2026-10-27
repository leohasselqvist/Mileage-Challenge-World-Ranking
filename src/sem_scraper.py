import bs4
import requests
import pandas as pd

classes = ["P", "UC"]

energy_types = ["ICE", "H2", "BE"]

event_slugs_by_year = {
    2026: ["sem_2026_pl", "sem_2026_br", "sem_2026_us", "sem_2026_qa"],
    2025: ["sem_2025_eu", "sem_2025_br", "sem_2025_us", "sem_2025_as"],
    2024: ["sem_2024_eu", "sem_2024_br", "sem_2024_us", "sem_2024_as", "sem_2024_cn"],
}

def scrape_event_results(year, event_slug, class_name, energy_type):
    url = f"https://results.sem-app.com/app/{event_slug}/{class_name}/{energy_type}"
    print(f"[*] Scraping {year} {event_slug} {class_name} {energy_type} from {url}...")
    try:
        r = requests.get(url, timeout=5)
        soup = bs4.BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"[!] Failed {url}: {e}")
        return None

    track_results = soup.find(id="RR").find_all("tr")

    #with open("test.html", "w") as f:
    #    f.write(track_results.prettify())
    records = []

    for team in track_results:
        rank = team.find("td", class_="col1").text.strip()
        country = team.find("td", class_="col2 wide").find("img")["title"].strip()
        num = int(team.find("td", class_="col3").text.strip())
        institution = team.find("td", class_="col4").find("span").text.strip()
        uuid = team.find("td", class_="col4").find("a")["href"].split("/")[-1].strip()
        name = team.find("td", class_="col4").find("a").text.strip()
        attempts = int(team.find("td", class_="col5 wide").find("span").text[0].strip())
        max_attempts = int(team.find("td", class_="col5 wide").find("span").text[5].strip())
        try:
            best_result = int(team.find("td", class_="col6").find("span", class_="si").text.replace(",", "").strip())
        except AttributeError:
            best_result = 0

        records.append({
            "event_id": event_slug,
            "year": year,
            "vehicle_class": class_name,
            "propulsion_type": energy_type,
            "rank": rank,
            "team_id": uuid,
            "country": country,
            "vehicle_number": num,
            "institution": institution,
            "team_name": name,
            "attempts_recorded": attempts,
            "attempts_max": max_attempts,
            "best_efficiency": best_result
        })
    return records



def __main__():
    event_records = []
    for year, event_slugs in event_slugs_by_year.items():
        for event_slug in event_slugs:
            for class_name in classes:
                for energy_type in energy_types:
                    print(f"[*] Scraping {year} {event_slug} {class_name} {energy_type}...")
                    event_records.extend(scrape_event_results(year, event_slug, class_name, energy_type))
            df = pd.DataFrame(event_records)
            df.to_csv(f"../data/{year}/{event_slug}.csv", index=False)
            event_records = []  # Reset for next event


if __name__ == "__main__":
    __main__()