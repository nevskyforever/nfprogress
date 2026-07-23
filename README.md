# nfprogress

nfprogress is a desktop progress tracker for writers. It helps you organize
writing projects, set goals and deadlines, record completed work, and review
your writing statistics. Optional game mechanics add rewards and challenges
for writers who prefer extra motivation.

## Features

- Track multiple writing projects and their stages.
- Set project goals, daily targets, and deadlines.
- Record progress in characters, A4 pages, author's sheets, or Ficbook pages.
- Review project statistics, productive days, and writing streaks.
- Count text from Microsoft Word (`.docx`) and Scrivener projects.
- Use infinite projects for ongoing work without a fixed final goal.
- Enable optional game mechanics with experience, coins, quests, items,
  rewards, and streak freezes.
- Check for and install application updates.

## Supported platforms

- Windows
- macOS on Apple Silicon
- macOS on Intel

## Download

Download the latest build from
[GitHub Releases](https://github.com/nevskyforever/nfprogress/releases).
Project downloads are also published through
[nfproject.ru](https://nfproject.ru/).

## Running from source

Python 3.11 is used for the official Windows build.

1. Clone the repository:

   ```bash
   git clone https://github.com/nevskyforever/nfprogress.git
   cd nfprogress
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows:

   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install the runtime dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   python main_UI.py
   ```

## Code signing policy

Free code signing provided by
[SignPath.io](https://signpath.io/), certificate by
[SignPath Foundation](https://signpath.org/).

### Project roles

- Committer, reviewer and approver: nevskyforever

### Privacy policy

nfprogress does not transfer information to other networked systems unless
specifically requested by the user while using a network-dependent feature.

## License

nfprogress is free and open-source software licensed under the
[GNU General Public License version 3](LICENSE).

