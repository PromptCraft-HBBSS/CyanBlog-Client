# Client-Side

A rich-based python REPL interface.

Dependencies:
- requirements.txt
- vim (could be replaced for editor of favour)
- nodejs

Be sure to replace `dotenv_path` and `docs_dir` to your actual path.

## Running

```sh
mkdir docs;
mkdir downloads;

touch .env; echo "PULL_KEY='your_pull_key_here'
DELETE_KEY='your_delete_key_here'
PUSH_KEY='your_push_key_here'
API_URL='http://your_server_hostname_here/'" > .env;

cd preview/;
npm install;
node server.js; # Opens up preview server at localhost:8001
cd ../;
conda create -n cyan;
conda activate cyan;
pip install -r requirements.txt;
python3 ./main.py; # Opens up repl
```

Then open up http://localhost:8001/ in a browser to see the preview.
