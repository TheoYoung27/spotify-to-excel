This project is a simple webserver on localhost:3000 which takes spotify playlists and attempts to find audio versions of the songs on youtube,
downlaods them, stores them in a google drive folder, records the song information and appends to a specified google doc spreasheet. It requires logging in to both google and spotify.

attempting to login to spotify with google causes issues with the cookie storage.
This was created to make my life easier for uploading songs to SUNY Oswego's radio stations, WNYO, and will likely be of little use to you if you are not using the program to do this.

in order for this to run on your own machine, you will need to create an app using the spotify developer api at https://developer.spotify.com/dashboard
as well as create a project on google's developer console at https://console.cloud.google.com/home/dashboard
the google project will require the openid scope as well as the restricted scope which allows your app to see, edit, create, and delete all of your Google Drive files.

after registering the apps with both spotify and google, add a file called auth.py to your project in the root directory, and add these six things:
1. SPOTIFY_CLIENT_SECRET = the client secret visible on the project's page on the spotify dashboard
2. SPOTIFY_CLIENT_ID = find this in the same spot as the previous point
3. SPOTIFY_REDIRECT = same as before, listed under 'Redirect URIs'
4. GOOGLE_CLIENT_SECRET = found in the google console, by navigating to the credentials screen and clicking to edit your OAuth 2.0 Client ID for your previously created project.
5. GOOGLE_CLIENT_ID = found on the same page as the previous point
6. GOOGLE_REDIRECT = whatever you assigned as your Authorized Redirect URI, found on the same page as the two previous points

If you wish to change the port from 3000 to another localhost port, modify the port variable in app.py, and ensure that the port number is consistent for your projects on the google
and spotify developer consoles.
