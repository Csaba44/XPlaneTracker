# Task 1
When I tag a file, it is automatically built and released on github. I am planning on making my repo private, and I'd like to upload my built python app to my website so authorized people can download it directly from there and i can make my repo private.
You need to come up with an industry standard idea, and decide on how to implement it. Create a plan @docs/plans

The requirements are as follows:
- All versions should be downloadable
- Gives a checksum so users can compare
- When releasing, the github workflow automates everything without my intervention
- I can create a change log for it manually in some way that is displayed on the site
- No other person can upload a file except me as the owner
- Files are saved as .env.dev [APP_NAME]-v2.0.0 for example depending on the tag
- Only logged in users can download it
- It can support beta versions with a display on the frontend with a "beta" tag when released with tag number ending in "-beta"
- Signed urls - meaning urls expire
- Rate limiting
- Rollback support for latest
- Only supports windows for now
- Make a releases.json that will store all versions and are accessible without logging in
- Make support for in-app update checking
- An endpoint for the latest version that always points to the current latest version
- In the admin page admins can edit the releases, edit changelogs, and mark releases Deprecated
- Use cloudflare R2 for releases

After we agreed on a plan, you should make a relase guide under @docs telling me how can i release, what is the exact flow, how to edit changelog, mark as deprecated, etc. Please make sure to ask me what about R2 keys, etc and DO NOT expose them in the github repo no matter what, always store them securely in a .env file!

# Task 2
Windows currently detects built binearies as viruses. Please walk me through how we will sign the bineary, and how will we make sure it is not detected as a virus as it has no malicious intent.

# Task 3
Please make sure to save the user's last simulator choice in some settings file, and load it whenever a new flight is started or the app is opened!