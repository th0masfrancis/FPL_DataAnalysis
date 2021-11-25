import requests
import yaml
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import json
from datetime import date

# setting options
pd.set_option('mode.chained_assignment', None)
sns.set()
plt.figure()


def get_fpl_data():
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    if config['last_updated'] != str(date.today()):
        print("Fetching player data from fpl website")
        r = requests.get(config['fpl_url'])
        json_file = r.json()

        with open('datadump.json', 'w+') as j:
            json.dump(json_file, j)

        # Update the config
        config['last_updated'] = str(date.today())
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

    else:
        print("Fetching player data from jsondump")
        with open('datadump.json') as j:
            json_file = json.load(j)

    elements_df = pd.DataFrame(json_file['elements'])
    element_types_df = pd.DataFrame(json_file['element_types'])
    teams_df = pd.DataFrame(json_file['teams'])
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

    # remove players with total_points < 0
    # main_df = main_df.loc[main_df['total_points'] > 0]
    # print(main_df.dtypes)

    return main_df


def data_preprocessing_my_team(my_fpl_team, main_df):
    my_fpl_team['position'] = my_fpl_team.element.map(main_df.set_index('id').element_type)

    my_fpl_team = pd.merge(my_fpl_team, main_df, how='left', left_on='element', right_on='id')
    # Replace the internal id with web_name
    my_fpl_team['element'] = my_fpl_team.element.map(main_df.set_index('id').web_name)

    return my_fpl_team


def get_my_team(game_week=12, team_id=296501):
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    url = config['base'].replace("gameweek", str(game_week))
    url = url.replace("teamid", str(team_id))
    r = requests.get(url)
    json = r.json()
    my_team = pd.DataFrame(json['picks'])
    return my_team


def plot_data(my_team, y='total_points', x='now_cost'):
    ax = sns.regplot(data=my_team, x=x, y=y, label='element_type')
    print(my_team.columns)
    for i in range(len(my_team)):
        plt.text(x=my_team.loc[i,x], y=my_team.loc[i,y], s=my_team.loc[i,'web_name'])
    plt.show()


def get_player_type_df(all_players, player_type):
    player_type_df = all_players[all_players['element_type'].isin([player_type])]
    player_type_df = player_type_df[player_type_df['total_points'] > 0]
    player_type_df = player_type_df.reset_index()
    return player_type_df


def get_player_info(player_id):
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    url = config['player_info'].replace('{element_id}', str(player_id))

    r = requests.get(url)
    json = r.json()
    return pd.DataFrame(json['history'])


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
    main_df_forwards = get_player_type_df(main_df, 'Forward')
    main_df_midfielders = get_player_type_df(main_df, 'Midfielder')
    main_df_defenders = get_player_type_df(main_df, 'Defender')
    main_df_goalkeepers = get_player_type_df(main_df, 'Goalkeeper')

    # Get player history
    # Calculate average points and standard deviation

    # Plot

    plot_data(my_team)
    # plot_data(main_df_midfielders)

    # Create a dataframe with all players weekly history len(main_df)
    main_history_df = pd.DataFrame()
    for player_id in main_df_forwards['id']:
        main_history_df = main_history_df.append(get_player_info(player_id))
    # Add names of the players
    main_history_df['web_name'] = main_history_df.element.map(main_df.set_index('id').web_name)
    main_history_df['opponent_team'] = main_history_df.opponent_team.map(teams_df.set_index('id').short_name)
    main_history_df.to_csv('player_history.csv')

    # print(main_history_df[df_filters['player_info_short']])

    # Mean and td calculation
    result_df = main_history_df.groupby('web_name', as_index=False)['total_points'].aggregate([np.mean, np.std])
    result_df.reset_index(inplace=True)
    plot_data(result_df,x='std',y='mean')
    print (result_df)
    plot_data(main_df_defenders)
    plot_data(main_df_goalkeepers)
    plot_data(main_df_midfielders)
    plot_data(main_df_forwards)



    plt.show()




if __name__ == '__main__':
    main()
