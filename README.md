# smallab
:small_blue_diamond: :microscope: :small_blue_diamond:

smallab (Small Lab) is an experiment framework designed to be easy to use with your experiment. 

The code in this repo should be understandable as a whole in at most 10 minutes.

## Features

* Easy to understand and simple
* Easy parallelization of experiments
* Only runs not previously completed experiments
* Hooks allow monitoring batch progress
* All parameters to methods use the typing module

## Installation


pip install smallab

or clone here from source


## Usage
Check out demo.py (Copied here)

```python
import typing
import random
import os
import pickle

#What you need to import from smallab
from smallab.experiment import Experiment
from smallab.runner import ExperimentRunner


#Write a simple experiment
class SimpleExperiment(Experiment):
    #Need to implement this method, will be passed the specification
    #Return a dictionary of results
    def main(self, specification: typing.Dict) -> typing.Dict:
        random.seed(specification["seed"])
        for i in range(specification["num_calls"]): #Advance the random number generator some amount
           random.random()
        return {"number":random.random()}

runner = ExperimentRunner()

#Optional: Add an on complete hook!
runner.on_specification_complete(lambda specification, result: print(result["number"]))

#Optional: Email yourself when the whole batch is done
#Read https://stackoverflow.com/questions/5619914/sendmail-errno61-connection-refused about how to start an stmp serevr
from smallab.utilities.email_hooks import email_on_batch_sucesss
runner.on_batch_complete(email_on_batch_sucesss("test@example.com",smtp_port=1025))
#Take it back off since we don't actually want to bother Mr. Test
runner.on_batch_complete(None)

#Set the specifications for our experiments, the author reccomends reading this from a json file!
specifications = [{"seed": 1,"num_calls":1}, {"seed":2,"num_calls":1}]

#Fire off the experiment
runner.run("random_number",specifications,SimpleExperiment())

#Read back our results
for fname in os.listdir(runner.get_batch_save_folder("random_number")):
    if "json" not in fname: #don't read back the completed file
        with open(os.path.join(runner.get_batch_save_folder("random_number"), fname), "rb") as f:
            results = pickle.load(f)
            print(results["specification"]["seed"])
            print(results["result"]["number"])


from smallab.specification_generator import SpecificationGenerator
#If you want to run a lot of experiments but not manual write out each one, use the specification generator.
#Note: This is also JSON serializable, so you could store this in a json file
generation_specification = {"seed":[1,2,3,4,5,6,7,8],"num_calls":[1,2,3]}

#Call the generate method. Will create the cross product.
specifications = SpecificationGenerator().generate(generation_specification)
print(specifications)

runner.run("random_number_from_generator",specifications,SimpleExperiment(),continue_from_last_run=True)

#Read back our results
for fname in os.listdir(runner.get_batch_save_folder("random_number_from_generator")):
    if "json" not in fname: #don't read back the completed file
        with open(os.path.join(runner.get_batch_save_folder("random_number_from_generator"), fname), "rb") as f:
            results = pickle.load(f)
            print(results["specification"]["seed"])
            print(results["result"]["number"])

```

## How it works
The ExperimentRunner class is passed a list of dictionaries of specifications. 
These dictionaries need to be json serializable.

The ExperimentRunner looks at the completed.json in the folder for the batch name (The name parameter of the .run method) and computes which experiments need to be run. 
The experiments that need to run are the specifications not in the completed.json.

The ExperimentRunner begins runnning the batch either in parallel or single threaded. 
If the parallel implementation is used each specification is joblib's threaded backend. 

Once all experiments are either completed or failed (They threw an exception) the results are saved as a pickle file. 
The results are saved in a dictionary that looks like {"specification": <the specification the experiment was passed>, "result": <what the experiment .main returned>}.

The return value of the experiment .main function must be pickle serializable. 

### Callbacks
The runner has several hooks which are called at different times. 

* `on_specification_complete` called whenever a specification completes running (Ususually a single experiment)
* `on_specification_falure` called whenver a specification fails running (Throws an exception)
* `on_batch_complete` called after runner `.run` has finished running, passed all the succesfully completed specifications
* `on_batch_failure` called after runner `.run` has finished running, passed all the failed specifications


### Folder Structure
Each experiment is saved in the following structure

* experiment_runs/

.* \<name\>/ #The name you provide to runner.run

..* <specification_hash>/ # A hash of the dictionary you provide as the specification

...* specification.json # The specification.json

...* <specification_hash>.pkl #The results dictionary