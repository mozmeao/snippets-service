"""
Comments stdin to the GitHub PR that triggered the travis build.

Usage:
    flake8 | python comment-on-pr.py

Notes:
    The following enviromental variables need to be set:
    - TRAVIS_PULL_REQUEST
    - TRAVIS_REPO_SLUG
    - TRAVIS_BOT_GITHUB_TOKEN
"""

import os
import sys
import json
import requests


def comment_on_pull_request(pr_number, slug, token, comment):
    """ Comment message on a given GitHub pull request. """
    url = 'https://api.github.com/repos/{slug}/issues/{number}/comments'.format(
        slug=slug, number=pr_number)
    response = requests.post(url, data=json.dumps({'body': comment}),
                             headers={'Authorization': 'token ' + token})
    return response.json()


if __name__ == '__main__':
    PR_NUMBER = os.environ.get('TRAVIS_PULL_REQUEST')
    REPO_SLUG = os.environ.get('TRAVIS_REPO_SLUG')
    TOKEN = os.environ.get('TRAVIS_BOT_GITHUB_TOKEN')

    results = sys.stdin.read()
    comment = (
        """
```
{flake_results}
```
        """).format(flake_results=results)

    if all([PR_NUMBER, REPO_SLUG, TOKEN, results.strip()]):
        comment_on_pull_request(PR_NUMBER, REPO_SLUG, TOKEN, comment)
    else:
        print 'Not all neccesery variables are present'
