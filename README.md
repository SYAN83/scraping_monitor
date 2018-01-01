# scraping_monitor

1. Add config.yml
2. Run flask with the following commands:

  a. Debugging mode:
  ```
  $ export FLASK_DEBUG=1
  $ python3 app.py
  ```
  
  b. Deployment: 
  ```
  $ nohup python3 monitor.py > monitor.log &
  ```
