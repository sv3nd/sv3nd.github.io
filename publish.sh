python3 -m venv ~/.virtualenvs/sv3ndk-blog
source ~/.virtualenvs/sv3ndk-blog/bin/activate
pip install -r requirements.txt

pelican content  -s publishconf.py
ghp-import output -b master

echo "now just run 'git push origin master'"

