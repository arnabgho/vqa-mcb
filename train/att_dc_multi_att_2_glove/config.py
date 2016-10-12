GPU_ID = 0
BATCH_SIZE = 8
VAL_BATCH_SIZE = 8
NUM_OUTPUT_UNITS = 3000 # This is the answer vocabulary size
MAX_WORDS_IN_QUESTION = 15
MAX_ITERATIONS = 1000000
PRINT_INTERVAL = 100
VALIDATE_INTERVAL = 1000000000
NUM_DC=20
SOLVER_STATE_LOAD='./result/_iter_120000.solverstate'
LOAD_SOLVER_STATE=True
# what data to use for training
TRAIN_DATA_SPLITS = 'train+val'

# what data to use for the vocabulary
QUESTION_VOCAB_SPACE = 'train+val'
ANSWER_VOCAB_SPACE = 'train+val'

# vqa tools - get from https://github.com/VT-vision-lab/VQA
VQA_TOOLS_PATH = '/home/arnabg/VQA/PythonHelperTools/'
VQA_EVAL_TOOLS_PATH = '/home/arnabg/VQA/PythonEvaluationTools/'

# location of the data
VQA_PREFIX = '/home/arnabg/VQA/'
GENOME_PREFIX = '/y/daylen/vqa/02_tools/genome/'
DATA_PREFIX = '/home/arnabg/MCB/vqa-mcb/preprocess/vqa_test_res5c/'
DC_PREFIX='/home/arnabg/densecap/'
DATA_PATHS = {
	'train': {
		'ques_file': VQA_PREFIX + '/Questions/OpenEnded_mscoco_train2014_questions.json',
		'ans_file': VQA_PREFIX + '/Annotations/mscoco_train2014_annotations.json',
		'features_prefix': DATA_PREFIX + '/resnet_res5c_bgrms_large/train2014/COCO_train2014_',
        'dc_file':DC_PREFIX+'/vt-captions-train/train_results_indexed.json',
        'dc_file_prefix':'COCO_train2014_'
	},
	'val': {
		'ques_file': VQA_PREFIX + '/Questions/OpenEnded_mscoco_val2014_questions.json',
		'ans_file': VQA_PREFIX + '/Annotations/mscoco_val2014_annotations.json',
		'features_prefix': DATA_PREFIX + '/resnet_res5c_bgrms_large/val2014/COCO_val2014_',
        'dc_file':DC_PREFIX+'/vt-captions-val/val_results_indexed.json',
        'dc_file_prefix':'COCO_val2014_'

	},
	'test-dev': {
		'ques_file': VQA_PREFIX + '/Questions/OpenEnded_mscoco_test-dev2015_questions.json',
		'features_prefix': VQA_PREFIX + '/resnet_res5c_bgrms_large/test2015/COCO_test2015_',
        'dc_file':DC_PREFIX+'/vt-captions-test/test_results_indexed.json',
        'dc_file_prefix':'COCO_test2015_'
	},
	'test': {
		'ques_file': VQA_PREFIX + '/Questions/OpenEnded_mscoco_test2015_questions.json',
		'features_prefix': VQA_PREFIX + '/resnet_res5c_bgrms_large/test2015/COCO_test2015_',
        'dc_file':DC_PREFIX+'/vt-captions-test/test_results_indexed.json',
        'dc_file_prefix':'COCO_test2015_'
	},
	# TODO it would be nice if genome also followed the same file format as vqa
	'genome': {
		'genome_file': GENOME_PREFIX + '/question_answers_prepro.json',
		'features_prefix': DATA_PREFIX + '/genome/Features/resnet_res5c_bgrms_large/whole/'
	}
}
