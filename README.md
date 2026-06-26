# NSWindose
Needy Streamer Overload PC (.es3) -> Nintendo Switch (.dat) save converter
![App Screenshot](/media/ig.png)
# Usage
1. Back up Needy Streamer Overload save data from your switch and move it to a computer. This can be done with [JKSV](https://github.com/J-D-K/JKSV)
2. Extract ```.nx_save_meta.bin``` from the back up.
3. Navigate to the ```Windose_Data``` folder inside of Needy Streamer Overload on your PC and run ```nso_converter.py``` inside.
4. A folder in the same directory called ```NSWindose``` should now exist. Navigate to that folder and send all of its contents to a .zip file. Add the .bin file extracted in step 2 into that same .zip file.
5. Copy that .zip file back to wherever you got your original save back up from. When using JKSV, it's ```\JKSV\NEEDY STREAMER OVERLOAD``` 


# Disclaimer
This was reverse-engineered from a single Day1 sample between both versions so theres a tiny possibility that keys from days later on won't convert. However, I say "tiny" because many events related to things you can't possibly see on day one were dug up and sucsesfully mapped. I've ran into no problems so far and the saves seem identical on both systems but you never know. Goes without saying; please remember to back up your saves.
