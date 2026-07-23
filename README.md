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

## Uninstallation

### Windows

Open **Settings > Apps > Installed apps**, find **nfprogress**, and select
**Uninstall**. The application is installed in
`%LOCALAPPDATA%\Programs\nfprogress`.

Uninstalling the application does not remove user data. It is stored in
`%APPDATA%\nfprogress`. Data created by older versions may also remain in
`%USERPROFILE%\Documents\nfprogress`. Delete these directories manually only
if you no longer need your projects, settings, and progress history.

### macOS

Move `nfprogress.app` from the Applications folder to the Trash. User data in
`~/Documents/nfprogress` is not removed automatically; delete that directory
manually only if you no longer need it.

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

- Committer: nevskyforever
- Reviewer: nevskyforever
- Approver: nevskyforever

### Privacy policy

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or
operating it.

## License

nfprogress is free and open-source software licensed under the
[GNU General Public License version 3](LICENSE).
