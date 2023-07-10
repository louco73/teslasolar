# teslasolar
Charge your Tesla with excess solar using Teslapy

This code works for me, and has been reasonably tested. However, the error handling is still suspect, so use at your own risk!

I have a Fronius inverter, but if your inverter has an API endpoint with a local IP address then you should be able to understand the output and change the code accordingly. You will need the additional Fronius power meters installed so you can measure solar export and house demand power levels.

Outstanding Issues:
  Error handling is still not well tested. I copied in someone else's code and haven't had time to refine it. Error messages are not printed cleanly.

Latest Improvements (July 10, 2023):

Checks the charge status every 5 mins and prints out the charging information.
If the car is within 2% of the charge limit then it checks every minute and stops charging once charged.
Cleaned up some logic that resulted in weird amp settings.
Checks if the charger is connected every 5 mins.
Now adjusts down to 2A to help remove stop/start issues with clouds

Possible Improvements:

If there is not enough solar it would be best to reduce the charging to 2A rather than stop. Then only stop after 2-3 mins if there is still not enough solar.
Break out the inverter code into a function to allow for other inverters to be added easily.

The code is reasonably well documented and self-explanatory. You need to configure the variables to suit your own environment, e.g. how much solar is needed before you start to consider charging, the minimum amps and maximum amps you can set with your charger, how long to wait once charging is stopped before checking again, etc.
