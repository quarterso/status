# Quarter status

The live status of Quarter's public services: https://status.quarterfi.com/

A GitHub Actions job checks each service every 10 minutes, from outside our servers, and publishes the page to GitHub Pages. A service is down after two failed checks 5 seconds apart. Going down opens an issue in this repository and coming back closes it, so watchers get an email.

History is kept for 30 days in the published `history.json`, not in git. Each run reads it, adds one check and publishes again.

- `check.py`: the checks and the page. Python standard library only.
- `python3 -m unittest discover -s tests`: the tests.

GitHub runs scheduled jobs late at busy times and turns them off in a public repository after 60 days with no commits. Push a commit at least every 60 days.
