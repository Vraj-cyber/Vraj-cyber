"""Refresh public-only profile cards using GitHub REST and GraphQL APIs.

No third-party dependencies. API failures leave the committed cards unchanged.
"""
import collections
import datetime
import html
import json
import os
from pathlib import Path
import time
import urllib.request

USER = os.environ.get('PROFILE_USERNAME', 'Vraj-cyber')
TOKEN = os.environ['GITHUB_TOKEN']


def api(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    for attempt in range(3):
        try:
            request = urllib.request.Request('https://api.github.com/' + path, data=body, headers={
                'Authorization': 'Bearer ' + TOKEN,
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
                'User-Agent': 'profile-stats',
                'Content-Type': 'application/json',
            })
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            if isinstance(result, dict) and result.get('errors'):
                raise RuntimeError('GitHub GraphQL returned errors')
            return result
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def collect():
    repos = []
    page = 1
    while True:
        batch = api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        repos.extend(r for r in batch if not r['private'])
        if len(batch) < 100:
            break
        page += 1
    languages = collections.Counter()
    for repo in repos:
        if not repo['fork'] and repo['size']:
            languages.update(api(f"repos/{USER}/{repo['name']}/languages"))
    query = '''query($login:String!) { user(login:$login) {
      contributionsCollection { contributionCalendar { totalContributions } }
    } }'''
    result = api('graphql', {'query': query, 'variables': {'login': USER}})
    contributions = result['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']
    return {
        'updated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'public_repositories': len(repos),
        'followers': api(f'users/{USER}')['followers'],
        'stars_received': sum(r['stargazers_count'] for r in repos if not r['fork']),
        'contributions_last_year': contributions,
        'language_bytes_public_nonfork': dict(languages.most_common()),
    }


def main():
    data = collect()
    output = Path('assets')
    output.mkdir(exist_ok=True)
    temporary = output / 'stats.json.tmp'
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(output / 'stats.json')
    print('Updated public statistics:', data['public_repositories'], 'repositories;', data['contributions_last_year'], 'contributions')


if __name__ == '__main__':
    main()
