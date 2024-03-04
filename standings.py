import pandas as pd
from espn_api.basketball import League
from datetime import datetime
import pytz
import streamlit as st
import random

# calculate weighted points per week
def weighted_points(weekly_points, recent_weeks_weight=2, recent_weeks_count=4):
    total_weeks = len(weekly_points)
    weights = [recent_weeks_weight if week > total_weeks - recent_weeks_count else 1 for week in range(total_weeks)]
    weighted_points = sum(p * w for p, w in zip(weekly_points, weights))
    return weighted_points / sum(weights)

# calculate win probability
def win_probability(team1, team2, team_strengths):
    total_strength = team_strengths[team1] + team_strengths[team2]
    return team_strengths[team1] / total_strength

# compensate for h2h
def adjust_strength_for_head_to_head(team_strengths, head_to_head_results):
    for match in head_to_head_results:
        winner, loser = match
        if winner in team_strengths and loser in team_strengths:
            team_strengths[winner] += 1
            team_strengths[loser] -= 1
    return team_strengths

# calculate the strength of schedule
def calculate_strength_of_schedule(team, remaining_schedule, team_strengths):
    opponents_strength = sum(team_strengths[opponent] for week in remaining_schedule for opponent in week if team in week)
    return opponents_strength / len(remaining_schedule)

# simulate the season
def simulate_season(remaining_schedule, team_strengths, current_standings, total_weeks=20, simulations=10000, randomness_factor=0.05):
    playoff_chances = {team: 0 for team in team_strengths}
    last_place_chances = {team: 0 for team in team_strengths}

    # teams that cannot mathematically finish last
    mathematically_safe_from_last = {team for team, wins in current_standings.items() if wins > total_weeks / 2}

    for _ in range(simulations):
        standings = current_standings.copy()
        for week in remaining_schedule:
            for match in week:
                team1, team2 = match
                random_adjustment = 1 + randomness_factor * random.uniform(-1, 1)
                win_prob = win_probability(team1, team2, team_strengths) * random_adjustment
                if random.random() < win_prob:
                    standings[team1] += 1
                else:
                    standings[team2] += 1

        top_teams = sorted(standings, key=standings.get, reverse=True)[:4]
        for team in top_teams:
            playoff_chances[team] += 1

        last_place_team = sorted(standings, key=standings.get)[0]
        last_place_chances[last_place_team] += 1

    for team in playoff_chances:
        playoff_chances[team] = (playoff_chances[team] / simulations) * 100
        if team in mathematically_safe_from_last:
            last_place_chances[team] = 0  #set to 0 for teams mathematically safe from last
        else:
            last_place_chances[team] = (last_place_chances[team] / simulations) * 100

    return playoff_chances, last_place_chances


def main():
    # api stuff
    league_id = 1800187247
    year = 2024
    espn_s2 = 'AEC5UWfHuxcu831I73sNZEH4je3W%2FNNxVN4clK3USlazw8tVGSw2qLuTZdyLIKU6HlMpgsz0mZ0OMY%2F2SUwmALZ0YwRQBj41kvt3xawnde4YVncFCxfFz48ZUAORsacFlEvwQlPlbzTp3i%2BmUMALHNhQn5Yn%2Fhah9T5VSERo40psL0U30cbbZfxSoNirW4pueHAcykhIYumCo03uVMlEhObQIaDBBy9Kx2MLOBsGFuHymKx7ndXDPHhB4E1uWur9IGAWmF8GW8zq7NaEgr6DG4Bw'
    swid = '{6E7237F4-5305-42FE-B237-F45305D2FE66}'
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    # manual data import cause rish screwed it all up
    data = {
        "Team": ["Thunderstruck", "White Lightning", "Ant-Man and the BI", "Mark Will didnt make it", "TJ's Tall Boys", "Bucksketball", "LameloBawl", "Bum Squad", "Tel Aviv Basketball Club", "Bibliomaniacs"],
        "Record": ["13-5", "14-4", "10-8", "7-11", "9-9", "11-7", "7-11", "7-11", "6-12", "6-12"]
    }
    df_new = pd.DataFrame(data)
    current_date = datetime.now(pytz.timezone('US/Eastern'))

    # weeks since the start of the season
    season_start_date = datetime(2023, 10, 24, tzinfo=pytz.timezone('US/Eastern'))
    num_weeks = ((current_date - season_start_date).days // 7) - 1

    # weekly points data for each team
    weekly_team_points = {team.team_name: [0]*num_weeks for team in league.teams}
    for week in range(1, num_weeks + 1):
        box_scores = league.box_scores(week)
        for box in box_scores:
            weekly_team_points[box.home_team.team_name][week - 1] = box.home_score
            weekly_team_points[box.away_team.team_name][week - 1] = box.away_score
        
    # get the remaining schedule
    remaining_schedule = []
    for week in range(num_weeks + 1, 21):  # 20-week season
        matchups = league.scoreboard(week)
        week_schedule = [(match.home_team.team_name, match.away_team.team_name) for match in matchups]
        remaining_schedule.append(week_schedule)

    # team strengths based on weighted points per week
    team_strengths = {team: weighted_points(points) for team, points in weekly_team_points.items()}

    for team in team_strengths.keys():
        sos = calculate_strength_of_schedule(team, remaining_schedule, team_strengths)
        team_strengths[team] += sos

    # total and average points
    df_new['PF'] = df_new['Team'].map(weekly_team_points).apply(sum)
    df_new['Total Weeks'] = df_new['Record'].apply(lambda x: sum(map(int, x.split('-'))))
    df_new['PF/Wk'] = (df_new['PF'] / df_new['Total Weeks']).round(1)
    

    # current standings from the DataFrame
    current_standings = {row["Team"]: int(row["Record"].split('-')[0]) for index, row in df_new.iterrows()}

    playoff_probabilities, last_place_probabilities = simulate_season(remaining_schedule, team_strengths, current_standings)

    # add probabilities to DataFrame
    df_new['Playoff Chance %'] = df_new['Team'].map(playoff_probabilities).apply(lambda x: f"{x:.1f}%" if x >= 1 else ("<0.1%" if x > 0 else "0%"))
    df_new['Last Place Chance %'] = df_new['Team'].map(last_place_probabilities).apply(lambda x: f"{x:.1f}%" if x >= 1 else ("<0.1%" if x > 0 else "0%"))


    # sort DataFrame by wins and then by PF
    df_new[['Wins', 'Losses']] = df_new['Record'].str.split('-', expand=True).astype(int)
    df_new.sort_values(by=['Wins', 'PF'], ascending=[False, False], inplace=True)

    # drop unnecessary columns
    df_new.drop(['Wins', 'Losses', 'Total Weeks'], axis=1, inplace=True)
    df_new = df_new.round()
    df_new['PF'] = df_new['PF'].astype(int).round(1)
    df_new['PF/Wk'] = df_new['PF/Wk'].astype(int).round(1)

    # streamlit code for displaying the DataFrame
    st.title("White Man Can't Jump Standings")
    st.write("Rish is a bot and fat")
    st.write("PF includes the current week's points. Playoff chances are estimated probabilities.")

    # reset the index
    df_new.reset_index(drop=True, inplace=True)
    df_new.index += 1

    # highlight the top four rows
    def color_top_four(val):
        color = 'green' if val.name < 5 else 'none'
        return [f'background-color: {color}' if color != 'none' else '' for _ in val]
    st.dataframe(df_new.style.apply(color_top_four, axis=1))

if __name__ == "__main__":
    main()