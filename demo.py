if __name__ == "__main__":

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
    runner.on_batch_complete_function = None

    #Set the specifications for our experiments, the author reccomends reading this from a json file!
    specifications = [{"seed": 1,"num_calls":1}, {"seed":2,"num_calls":1}]

    #Fire off the experiment
    runner.run("random_number",specifications,SimpleExperiment())

    #Read back our results
    for fname in os.listdir(runner.get_save_directory("random_number")):
        if "json" not in fname: #don't read back the completed file
            with open(os.path.join(runner.get_save_directory("random_number"),fname),"rb") as f:
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
    for fname in os.listdir(runner.get_save_directory("random_number_from_generator")):
        if "json" not in fname: #don't read back the completed file
            with open(os.path.join(runner.get_save_directory("random_number_from_generator"),fname),"rb") as f:
                results = pickle.load(f)
                print(results["specification"]["seed"])
                print(results["result"]["number"])

