# teslasolar
Charge your Tesla with excess solar using Teslapy

This code works for me, but is not thoroughly tested. Use at your own risk!

I have a Fronius inverter, but if your inverter has an API endpoint with a local IP address then you should be able to understand the output and change the code accordingly.

Outstanding Issues:
  I've not tested what happens when the car has finished charging.

The code is reasonably well documented and self-explanatory. You need to configure the variables to suit your own environment, e.g. how much solar is needed before you start to consider charging, the minimum amps and maximum amps you can set with your charger, how long to wait once charging is stopped before checking again, etc.
