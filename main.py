import requests
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def get_FPL_data():
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        r = requests.get(config['fpl_url'])
        json = r.json()
        elements_df = pd.DataFrame(json['elements'])
        element_types_df = pd.DataFrame(json['element_types'])
        teams_df = pd.DataFrame(json['teams'])
    return elements_df, element_types_df, teams_df


def get_filters():
    with open('df_filters.yaml') as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def data_preprocessing(main_df, player_types_df, teams_df):
    # Replacing the team code in main dataframe with shortnames from teams look up dataframe
    team_names = teams_df.loc[:, ('id', 'name')]
    team_names.set_index('id', inplace=True, drop='id')
    team_names_dict = team_names['name'].to_dict()
    # print(team_names_dict)
    pd.set_option('mode.chained_assignment', None)
    main_df.loc[:, 'team'] = main_df.loc[:, 'team'].map(team_names_dict)
    main_df['element_type'] = main_df.element_type.map(player_types_df.set_index('id').singular_name)

    # Convert to float total points and value season
    main_df['form'] = main_df['form'].astype('float')
    main_df['points_per_game'] = main_df['points_per_game'].astype('float')
    main_df['value_season'] = main_df['value_season'].astype('float')
    main_df['ict_index'] = main_df['ict_index'].astype('float')
    # print(main_df.dtypes)


    return main_df


def main():
    # get Data from FPL website
    players_df, player_types_df, teams_df = get_FPL_data()

    # Load the filters that needs to be applied on FPL data, from df_filter.yaml
    df_filters = get_filters()
    main_df = players_df[df_filters['player_filter']]

    # pre-process the filtered data
    main_df = data_preprocessing(main_df, player_types_df, teams_df)

    print(main_df[df_filters['player_filter_short']])

    position_group = np.round(
        main_df.groupby('element_type', as_index=False).aggregate({'value_season': np.mean, 'total_points': np.mean}), 2)
    print(position_group.sort_values('value_season', ascending=False))


if __name__ == '__main__':
    main()
