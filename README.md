# err-seat

Seat Api Interface for errbot, reports starbases (out of fuel, silo full, siphon, reinforced). 
Ability to search for pocos/posses, offline posses, posses that run out of fuel in x hours. 
Announcement of courier contracts and its updates.
Announcement of corp sales.

## Warning

The whole POS and POCO Code is not tested against seat 3.0 api version 2.0. Feel free to fork and do a pull request if you are using that. 

## Installation

You need errbot and eveseat please see the following links for setting that up:

- http://errbot.io
- http://seat-docs.readthedocs.io/en/latest/

## Connecting / Configuration

Under https://yourseatdomain.com/api-admin add the ip of your errbot instance.
In the seat.py you need to set the api url and the token you just generated plus the additional settings.

Example:
```
!plugin config seat
{'CHECK_CONTRACTS': True,               # check for courier updates
 'CHECK_STRUCTURES': True,              # check for pos
 'SEAT_URL': '<your_seat_url>',         # seat url
 'SEAT_TOKEN': '<seat_token>',          # seat token
 'REPORT_CONTRACTS_CHAN': '<channel>',  # report couriers here
 'REPORT_POS_CHAN': '<channel>',        # report posses here
 'REPORT_REINF_CHAN': '<channel>',      # report reinforcements here
 'REPORT_TRADES_CHAN': '<channel>',     # report trades here
 'FUEL_THRESHOLD': 24,                  # fuel threshold for starbases
 'STRONT_THRESHOLD': 12,                # stront threshold
 'CHECK_TRADES': True,                  # check for trades
 'TRADECORP_ID': '<corpid>'}            # id of tradecorp

```

## Help Call Example

seat

Seat API to errbot

```
- !poco find - Finds all pocos in given <system>, Usage !poco find <system>
- !pos clearwarnings - Clears all saved warning states
- !pos find - Finds all towers in given <system>, Usage !pos find <system>
- !pos offline - Finds all offline towers, Usage: !pos offline
- !pos oof - Finds all towers that will be running out of fuel in the given timeframe, Usa...
- !pos oos - Finds all towers that have no stront, Usage: !pos oos
- !pos reinforced - Finds all reinforced towers , Usage: !pos reinforced
plus a few admin commands which are documented in the code itself.
```

## misc

only tested against discord.py with errbot 4.2.2+.  
Keep in mind that eve api and seat api data is delayed.

## Contact

If you got questions catch me on gitter https://gitter.im/errbotio/errbot
