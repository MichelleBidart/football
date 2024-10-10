import awswrangler as wr
import utils.redshift_utils as redshift_utils
from datetime import datetime


def get_total_gols_for_liga(conn):
    query = """
    SELECT  
        l.league_name,
        m.season_year,
        SUM(m.home_score) AS total_goles_local,
        SUM(m.away_score) AS total_goles_visitante,
        SUM(m.home_score + m.away_score) AS total_goles
    FROM 
        "2024_michelle_bidart_schema".match m 
    INNER JOIN 
        "2024_michelle_bidart_schema".league l 
    ON 
        m.league_id = l.league_id 
    AND
        m.season_year = l.season_year
    GROUP BY 
        l.league_name, m.season_year;
    """

    df = wr.redshift.read_sql_query(sql=query, con=conn)


    df['execution_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return df

def get_results_by_team_for_current_leagues(conn):
    query = """WITH home_team_stats AS (
    SELECT 
        t.name AS team_name,
        m.season_year,
        l.league_name,
        SUM(CASE WHEN m.home_score > m.away_score THEN 1 ELSE 0 END) AS local_victory,
        SUM(CASE WHEN m.home_score = m.away_score THEN 1 ELSE 0 END) AS local_tie,
        SUM(CASE WHEN m.home_score < m.away_score THEN 1 ELSE 0 END) AS local_defeat
    FROM 
        "2024_michelle_bidart_schema".match m
    INNER JOIN 
        "2024_michelle_bidart_schema".team t ON m.team_home_id = t.id
    INNER JOIN 
        "2024_michelle_bidart_schema".league l ON m.league_id = l.league_id
        AND m.season_year = l.season_year
    WHERE 
        l.current = TRUE
    GROUP BY 
        t.name, m.season_year, l.league_name
),
away_team_stats AS (
    SELECT 
        t.name AS team_name,
        m.season_year,
        l.league_name,
        -- Solo estadísticas de visitante
        SUM(CASE WHEN m.away_score > m.home_score THEN 1 ELSE 0 END) AS away_victory,
        SUM(CASE WHEN m.away_score = m.home_score THEN 1 ELSE 0 END) AS away_tie,
        SUM(CASE WHEN m.away_score < m.home_score THEN 1 ELSE 0 END) AS away_defeat
    FROM 
        "2024_michelle_bidart_schema".match m
    INNER JOIN 
        "2024_michelle_bidart_schema".team t ON m.team_away_id = t.id
    INNER JOIN 
        "2024_michelle_bidart_schema".league l ON m.league_id = l.league_id
        AND m.season_year = l.season_year
    WHERE 
        l.current = TRUE
    GROUP BY 
        t.name, m.season_year, l.league_name
)
SELECT 
    COALESCE(h.team_name, a.team_name) AS team_name,
    COALESCE(h.season_year, a.season_year) AS season_year,
    COALESCE(h.league_name, a.league_name) AS league_name,
    COALESCE(local_victory, 0) + COALESCE(away_victory, 0) AS total_victory,
    COALESCE(local_tie, 0) + COALESCE(away_tie, 0) AS total_tie,
    COALESCE(local_defeat, 0) + COALESCE(away_defeat, 0) AS total_defeat,
    COALESCE(local_victory, 0) AS local_victory,
    COALESCE(local_tie, 0) AS local_tie,
    COALESCE(local_defeat, 0) AS local_defeat,
    COALESCE(away_victory, 0) AS away_victory,
    COALESCE(away_tie, 0) AS away_tie,
    COALESCE(away_defeat, 0) AS away_defeat
FROM 
    home_team_stats h
FULL OUTER JOIN 
    away_team_stats a
ON 
    h.team_name = a.team_name 
    AND h.season_year = a.season_year
    AND h.league_name = a.league_name
ORDER BY 
    team_name, season_year, league_name;
"""

    df = wr.redshift.read_sql_query(sql=query, con=conn)
    df['execution_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return df


def insert_results_to_redshift(df, conn, new_table):

    wr.redshift.to_sql(
        df=df,
        con=conn,
        schema="2024_michelle_bidart_schema",
        table = new_table,
        mode="replace"  
    )


def get_statistics():
    conn = redshift_utils.get_redshift_connection()
    df = get_total_gols_for_liga(conn)
    insert_results_to_redshift(df, conn, 'league_goal_statistics')
    df = get_results_by_team_for_current_leagues(conn)
    insert_results_to_redshift(df, conn, 'results_team_by_leagues')
