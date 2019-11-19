import logging

logging.config.fileConfig('logging.log',level=logging.INFO,format='%(asctime)s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

def __default_on_failure():
	logging.debug('!!! Failure !!!')

def on_specification_complete():
	logging.info('on_specification_complete')

def on_specification_failure():
	logging.debug('on_specification_failure')

def on_batch_complete():
	logging.info('on_batch_complete')

def on_batch_failure():
	logging.debug('on_batch_failure')

def set_experiment_folder():
	logging.info('set_experiment_folder')

def get_save_directory():
	logging.info('get_save_directory')

def get_save_file():
	logging.info('get_save_file')

def find_uncompleted_specifications():
	logging.info('find_uncompleted_specifications')

def run()：
	logging.info('run')

def __run_and_save()：
	logging.info('__run_and_save')

