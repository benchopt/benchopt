Quick explanations on how to add properly electric consumptions for Benchopt : 
- Modify TDP value with 2 possibilities :  
  - Ask the user which TDP he wants to use (probably annoying)
  - Automatic detection of the hardware (CPU or GPU) and get the correct TDP for the calculation
- In order to make it work with AIPowerMeter (Software made for a Cluster to collect data consumption of slurm jobs), we need to :
  - Add a new stored data : In callback.py, we need to store the duration of a run AND the date. With this, with a post treatment first, we will be able to fit the consumption with AIPowerMeter measures and to get the correct consumption.
  - The post treatment program will probably take as input the .parquet file to add/modify a column of data. With this we will be able to print it in benchopt. 

It will be easier to do it with a post treatment since AIPowerMeter record in real time electric consumptions but the script that uses the data to process it run one time per day.