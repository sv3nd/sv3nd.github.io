python3 -m venv ~/.virtualenvs/sv3ndk-blog
source ~/.virtualenvs/sv3ndk-blog/bin/activate
pip install -r requirements.txt

pelican content
cd output
python -m  http.server
cd $OLDPWD

