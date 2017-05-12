rm -r deploy.json
python concat_files.py
aws cloudformation deploy --template-file deploy.json --stack-name $1 --capabilities CAPABILITY_IAM
