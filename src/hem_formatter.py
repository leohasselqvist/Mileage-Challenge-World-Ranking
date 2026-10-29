import pandas as pd
import argparse

hem_columns = ['rank', 'vehicle_number', 'best_efficiency', 'team_name']
sem_columns = ['event_id', 'year', 'vehicle_class', 'propulsion_type', 'rank', 'team_id', 'country', 'vehicle_number', 'institution', 'team_name', 'attempts_recorded', 'attempts_max', 'best_efficiency']

def extract_hem_data(hem_data_path: str) -> pd.DataFrame:
  with open(hem_data_path, 'r', encoding="utf-8") as f:
    lines = f.readlines()
    data = []
    for line in lines:
      nameFound = False
      datapoints = line.strip().split(' ')
      team_data = []
      team_name = ''
      for i in range(len(datapoints)):
        try:
          team_data.append(float(datapoints[i]))
          if nameFound:
            if len(team_data) <= 2:
              team_data.insert(0, '-')
            team_data.append(team_name.strip())
            data.append(team_data)
            break
        except ValueError:
          team_name += datapoints[i] + ' '
          nameFound = True
  return pd.DataFrame(data, columns=hem_columns)

def convert_hem_to_sem(hem_df: pd.DataFrame, year: str, event_id: str, vehicle_class: str, propulsion_type: str) -> pd.DataFrame:
  sem_df = pd.DataFrame(index=hem_df.index, columns=sem_columns)
  sem_df['event_id'] = event_id
  sem_df['year'] = year
  sem_df['vehicle_class'] = vehicle_class
  sem_df['propulsion_type'] = propulsion_type
  sem_df['rank'] = hem_df['rank'].apply(lambda x: int(x) if x != '-' else '-')
  sem_df['team_id'] = hem_df['vehicle_number'].apply(lambda x: f"JP0000{int(x):02d}")
  sem_df['country'] = 'Japan'
  sem_df['vehicle_number'] = hem_df['vehicle_number'].apply(lambda x: int(x))
  sem_df['institution'] = ''
  sem_df['team_name'] = hem_df['team_name']
  sem_df['attempts_recorded'] = ''
  sem_df['attempts_max'] = ''
  sem_df['best_efficiency'] = hem_df['best_efficiency']
  return sem_df

def __main__():
  parser = argparse.ArgumentParser(description="Generate Shell Eco-marathon World Rankings.")
  parser.add_argument("--output", type=str, default="sem_data.csv", help="Output path for rankings CSV")
  parser.add_argument("--data", type=str, default="data/results/hem.txt", help="Folder containing HEM raw copy-paste data")
  parser.add_argument("--year", type=str, default="2026", help="Year of the event")
  parser.add_argument("--event-id", type=str, default="hem_2026_nc", help="Event ID for the SEM data")
  args = parser.parse_args()
  hem_data_path = f"{args.data}"
  hem_data = extract_hem_data(hem_data_path)
  print(f"Extracted {len(hem_data)} rows of HEM data from {hem_data_path}")
  print(hem_data.head())
  sem_data = convert_hem_to_sem(hem_data, year=args.year, event_id=args.event_id, vehicle_class='P', propulsion_type='ICE')
  print(f"Converted to {len(sem_data)} rows of SEM data")
  print(sem_data.head())
  sem_data.to_csv(args.output, index=False)
  print(f"Saved SEM data to {args.output}")
if __name__ == '__main__':
  __main__()