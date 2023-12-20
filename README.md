# BetterMafia

## How to Run
Once cloned, open in VS Code and navigate to project root directory in the terminal.

You will need to create your own virtual environment to run the project out of. To do this, first run: python -m venv game_env (this create a virtual environment called game_env)

Load into this environment by running: game_env\Scripts\activate

Then install all the dependencies by running: pip install -r requirements.txt

Now run: python app.py

Anytime you want to run the code, ensure you're running out of your virtual environment (it will be obvious in the terminal) first otherwise the project will not have access to the dependencies. The virtual environment ensures separation of packages between projects.
