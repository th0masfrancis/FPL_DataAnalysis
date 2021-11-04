import requests
import yaml
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# setting options
pd.set_option('mode.chained_assignment', None)
sns.set()
plt.figure()


def get_fpl_data():
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

    main_df.loc[:, 'team'] = main_df.loc[:, 'team'].map(team_names_dict)
    main_df['element_type'] = main_df.element_type.map(player_types_df.set_index('id').singular_name)

    # Convert to float total points and value season
    main_df['form'] = main_df['form'].astype('float')
    main_df['points_per_game'] = main_df['points_per_game'].astype('float')
    main_df['value_season'] = main_df['value_season'].astype('float')
    main_df['ict_index'] = main_df['ict_index'].astype('float')
    # print(main_df.dtypes)

    return main_df


def data_preprocessing_my_team(my_fpl_team, main_df):
    my_fpl_team['position'] = my_fpl_team.element.map(main_df.set_index('id').element_type)

    # logs_df = pd.merge(logs_df, employees_df, how='left',
    #         left_on='EmployeeID', right_on='EmployeeID')
    my_fpl_team = pd.merge(my_fpl_team, main_df, how='left', left_on='element', right_on='id')
    # Replace the internal id with webname
    my_fpl_team['element'] = my_fpl_team.element.map(main_df.set_index('id').web_name)

    return my_fpl_team


def get_my_team():
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        url = config['base'] + config['team_id'] + config['gameweek']
    r = requests.get(url)
    json = r.json()
    my_team = pd.DataFrame(json['picks'])
    return my_team


def main():
    # get data from FPL website
    players_df, player_types_df, teams_df = get_fpl_data()

    # Load the filters that needs to be applied on FPL data, from df_filter.yaml
    df_filters = get_filters()

    # Create a smaller dataframe for data processing
    main_df = players_df[df_filters['player_filter']]

    # Pre-process the filtered data
    main_df = data_preprocessing(main_df, player_types_df, teams_df)

    print(main_df[df_filters['player_filter_short']])

    position_group = np.round(
        main_df.groupby('element_type', as_index=False).aggregate({'value_season': np.mean, 'total_points': np.mean}),
        2)
    print(position_group.sort_values('value_season', ascending=False))

    my_team = get_my_team()

    # Identify top 6 players in each element_type who provides maximum value
    my_team = data_preprocessing_my_team(my_team, main_df)
    print(my_team[df_filters['player_filter_short']])

    # Plot
    ax = sns.barplot(data=my_team, x="web_name", y="total_points")
    plt.show()


if __name__ == '__main__':
    main()
