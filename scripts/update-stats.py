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
        'stars_received': sum(r['stargazers_count'] for r in repos if not r['fork']),
        'contributions_last_year': contributions,
        'language_bytes_public_nonfork': dict(languages.most_common()),
    }


def text(x, y, value, size=16, color='#BED0DB'):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="{color}">{html.escape(str(value))}</text>'


def card(title, description, content):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="235" viewBox="0 0 1000 235" role="img" aria-labelledby="t d">'
            f'<title id="t">{html.escape(title)}</title><desc id="d">{html.escape(description)}</desc>'
            '<rect x="1" y="1" width="998" height="233" rx="16" fill="#0B1521" stroke="#284253"/>' + content + '</svg>\n')


def render(data):
    content = text(32, 38, 'GITHUB AT A GLANCE', 15, '#67D8D4')
    items = [('public_repositories', 'Public repositories'), ('stars_received', 'Stars received'), ('contributions_last_year', 'Contributions · past year')]
    for index, (key, label) in enumerate(items):
        x = 32 + index * 325
        content += text(x, 106, f'{data[key]:,}', 42, '#F1F7FA') + text(x, 140, label, 17)
    content += text(32, 191, 'Public repository totals · contribution calendar reported by GitHub', 14)
    content += text(32, 216, 'Updated ' + data['updated_utc'], 13, '#8DAAB9')
    stats = card('GitHub statistics for ' + USER, '; '.join(f'{label}: {data[key]}' for key, label in items), content)
    counts = data['language_bytes_public_nonfork']
    total = sum(counts.values())
    content = text(32, 38, 'LANGUAGES IN PUBLIC CODE', 15, '#67D8D4')
    colors = ['#67D8D4', '#47A9B5', '#708EA6', '#B0C8D5', '#437481']
    if total:
        for i, (language, count) in enumerate(list(counts.items())[:5]):
            y = 70 + i * 27
            content += text(32, y, language, 15) + text(855, y, f'{count / total:.1%}', 15)
            content += f'<rect x="200" y="{y-11}" width="620" height="9" rx="4" fill="#183040"/>'
            content += f'<rect x="200" y="{y-11}" width="{620*count/total:.2f}" height="9" rx="4" fill="{colors[i]}"/>'
    else:
        content += text(32, 90, 'No public language data reported yet.')
    content += text(32, 216, 'Share of code bytes · owned, non-fork public repositories · not a proficiency ranking', 13, '#8DAAB9')
    return stats, card('Most-used programming languages', 'Language percentages based on GitHub Linguist code bytes.', content)


def main():
    data = collect()
    stats, languages = render(data)
    output = Path('assets')
    output.mkdir(exist_ok=True)
    # Fetch everything before writing so failed requests preserve the last good snapshot.
    for name, content in [('stats.svg', stats), ('languages.svg', languages), ('stats.json', json.dumps(data, indent=2) + '\n')]:
        temporary = output / (name + '.tmp')
        temporary.write_text(content)
        temporary.replace(output / name)
    print('Updated public statistics:', data['public_repositories'], 'repositories;', data['contributions_last_year'], 'contributions')


if __name__ == '__main__':
    main()
