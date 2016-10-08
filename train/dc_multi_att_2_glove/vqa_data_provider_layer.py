import caffe
import numpy as np
import re, json, random
import config
import spacy

QID_KEY_SEPARATOR = '/'
GLOVE_EMBEDDING_SIZE = 300

class VQADataProvider:

    def __init__(self, batchsize=config.BATCH_SIZE, max_length=15, mode='train'):
        self.batchsize = batchsize
        self.d_vocabulary = None
        self.batch_index = None
        self.batch_len = None
        self.rev_adict = None
        self.max_length = max_length
        self.mode = mode
        self.qdic, self.adic , self.dcdic= VQADataProvider.load_data(mode)

        with open('./result/vdict.json','r') as f:
            self.vdict = json.load(f)
        with open('./result/adict.json','r') as f:
            self.adict = json.load(f)

        self.n_ans_vocabulary = len(self.adict)
        self.nlp = spacy.load('en')
        self.glove_dict = {} # word -> glove vector

    @staticmethod
    def load_vqa_json(data_split):
        """
        Parses the question and answer json files for the given data split.
        Returns the question dictionary and the answer dictionary.
        """
        qdic, adic = {}, {}

        with open(config.DATA_PATHS[data_split]['ques_file'], 'r') as f:
            qdata = json.load(f)['questions']
            for q in qdata:
                qdic[data_split + QID_KEY_SEPARATOR + str(q['question_id'])] = \
                    {'qstr': q['question'], 'iid': q['image_id']}

        if 'test' not in data_split:
            with open(config.DATA_PATHS[data_split]['ans_file'], 'r') as f:
                adata = json.load(f)['annotations']
                for a in adata:
                    adic[data_split + QID_KEY_SEPARATOR + str(a['question_id'])] = \
                        a['answers']

        print 'parsed', len(qdic), 'questions for', data_split
        return qdic, adic
    @staticmethod
    def load_dc_json(data_split):
        with open(config.DATA_PATHS[data_split]['dc_file']) as f:
            json_data=json.load(f)
        return json_data
    @staticmethod
    def load_genome_json():
        """
        Parses the genome json file. Returns the question dictionary and the
        answer dictionary.
        """
        qdic, adic = {}, {}

        with open(config.DATA_PATHS['genome']['genome_file'], 'r') as f:
            qdata = json.load(f)
            for q in qdata:
                key = 'genome' + QID_KEY_SEPARATOR + str(q['id'])
                qdic[key] = {'qstr': q['question'], 'iid': q['image']}
                adic[key] = [{'answer': q['answer']}]

        print 'parsed', len(qdic), 'questions for genome'
        return qdic, adic

    @staticmethod
    def load_data(data_split_str):
        all_qdic, all_adic , all_dcdic= {}, {} , {}
        for data_split in data_split_str.split('+'):
            print("Data Splits")
            print(data_split)
            assert data_split in config.DATA_PATHS.keys(), 'unknown data split'
            if data_split == 'genome':
                qdic, adic = VQADataProvider.load_genome_json()
                all_qdic.update(qdic)
                all_adic.update(adic)
            else:
                qdic, adic = VQADataProvider.load_vqa_json(data_split)
                dc_dic=VQADataProvider.load_dc_json(data_split)
                all_qdic.update(qdic)
                all_adic.update(adic)
                all_dcdic.update(dc_dic)
        return all_qdic, all_adic , all_dcdic

    def getQuesIds(self):
        return self.qdic.keys()

    def getStrippedQuesId(self, qid):
        return qid.split(QID_KEY_SEPARATOR)[1]

    def getImgId(self,qid):
        return self.qdic[qid]['iid']

    def getQuesStr(self,qid):
        return self.qdic[qid]['qstr']

    def getAnsObj(self,qid):
        if self.mode == 'test-dev' or self.mode == 'test':
            return -1
        return self.adic[qid]

    def getDC(self,data_split,q_iid):
        return self.dcdic[config.DATA_PATHS[data_split]['dc_file_prefix']+str(q_iid).zfill(12) + '.jpg'  ]['captions'][0:config.NUM_DC]


    @staticmethod
    def seq_to_list(s):
        t_str = s.lower()
        for i in [r'\?',r'\!',r'\'',r'\"',r'\$',r'\:',r'\@',r'\(',r'\)',r'\,',r'\.',r'\;']:
            t_str = re.sub( i, '', t_str)
        for i in [r'\-',r'\/']:
            t_str = re.sub( i, ' ', t_str)
        q_list = re.sub(r'\?','',t_str.lower()).split(' ')
        q_list = filter(lambda x: len(x) > 0, q_list)
        return q_list

    def extract_answer(self,answer_obj):
        """ Return the most popular answer in string."""
        if self.mode == 'test-dev' or self.mode == 'test':
            return -1
        answer_list = [ answer_obj[i]['answer'] for i in xrange(10)]
        dic = {}
        for ans in answer_list:
            if dic.has_key(ans):
                dic[ans] +=1
            else:
                dic[ans] = 1
        max_key = max((v,k) for (k,v) in dic.items())[1]
        return max_key

    def extract_answer_prob(self,answer_obj):
        """ Return the most popular answer in string."""
        if self.mode == 'test-dev' or self.mode == 'test':
            return -1

        answer_list = [ ans['answer'] for ans in answer_obj]
        prob_answer_list = []
        for ans in answer_list:
            if self.adict.has_key(ans):
                prob_answer_list.append(ans)

        if len(prob_answer_list) == 0:
            if self.mode == 'val' or self.mode == 'test-dev' or self.mode == 'test':
                return 'hoge'
            else:
                raise Exception("This should not happen.")
        else:
            return random.choice(prob_answer_list)

    def qlist_to_vec(self, max_length, q_list):
        """
        Converts a list of words into a format suitable for the embedding layer.

        Arguments:
        max_length -- the maximum length of a question sequence
        q_list -- a list of words which are the tokens in the question

        Returns:
        qvec -- A max_length length vector containing one-hot indices for each word
        cvec -- A max_length length sequence continuation indicator vector
        glove_matrix -- A max_length x GLOVE_EMBEDDING_SIZE matrix containing the glove embedding for
            each word
        """
        qvec = np.zeros(max_length)
        cvec = np.zeros(max_length)
        glove_matrix = np.zeros(max_length * GLOVE_EMBEDDING_SIZE).reshape(max_length, GLOVE_EMBEDDING_SIZE)
        for i in xrange(max_length):
            if i < max_length - len(q_list):
                cvec[i] = 0
            else:
                w = q_list[i-(max_length-len(q_list))]
                if w not in self.glove_dict:
                    self.glove_dict[w] = self.nlp(u'%s' % w).vector
                glove_matrix[i] = self.glove_dict[w]
                # is the word in the vocabulary?
                if self.vdict.has_key(w) is False:
                    w = ''
                qvec[i] = self.vdict[w]
                cvec[i] = 0 if i == max_length - len(q_list) else 1

        return qvec, cvec, glove_matrix

    def answer_to_vec(self, ans_str):
        """ Return answer id if the answer is included in vocabulary otherwise '' """
        if self.mode =='test-dev' or self.mode == 'test':
            return -1

        if self.adict.has_key(ans_str):
            ans = self.adict[ans_str]
        else:
            ans = self.adict['']
        return ans

    def vec_to_answer(self, ans_symbol):
        """ Return answer id if the answer is included in vocabulary otherwise '' """
        if self.rev_adict is None:
            rev_adict = {}
            for k,v in self.adict.items():
                rev_adict[v] = k
            self.rev_adict = rev_adict

        return self.rev_adict[ans_symbol]

    def create_batch(self,qid_list):

        qvec = (np.zeros(self.batchsize*self.max_length)).reshape(self.batchsize,self.max_length)
        cvec = (np.zeros(self.batchsize*self.max_length)).reshape(self.batchsize,self.max_length)
        ivec = (np.zeros(self.batchsize*2048*14*14)).reshape(self.batchsize,2048,14,14)
        avec = (np.zeros(self.batchsize)).reshape(self.batchsize)
        glove_matrix = np.zeros(self.batchsize * self.max_length * GLOVE_EMBEDDING_SIZE).reshape(\
            self.batchsize, self.max_length, GLOVE_EMBEDDING_SIZE)
        dcvec=(np.zeros(self.batchsize*config.NUM_DC*self.max_length)).reshape(self.batchsize*config.NUM_DC,self.max_length)
        dc_glove_matrix = np.zeros(self.batchsize * config.NUM_DC * self.max_length * GLOVE_EMBEDDING_SIZE).reshape(\
            self.batchsize*config.NUM_DC, self.max_length, GLOVE_EMBEDDING_SIZE)
        dc_cvec=(np.zeros(self.batchsize*config.NUM_DC*self.max_length)).reshape(self.batchsize*config.NUM_DC,self.max_length)
        for i,qid in enumerate(qid_list):

            # load raw question information
            q_str = self.getQuesStr(qid)
            q_ans = self.getAnsObj(qid)
            q_iid = self.getImgId(qid)

            # convert question to vec
            q_list = VQADataProvider.seq_to_list(q_str)
            t_qvec, t_cvec, t_glove_matrix = self.qlist_to_vec(self.max_length, q_list)
            t_dclist=[]
            qid_split = qid.split(QID_KEY_SEPARATOR)
            data_split = qid_split[0]
            t_dclist=self.getDC(data_split,q_iid)
            try:
                if data_split == 'genome':
                    t_ivec = np.load(config.DATA_PATHS['genome']['features_prefix'] + str(q_iid) + '.jpg.npz')['x']
                else:
                    t_ivec = np.load(config.DATA_PATHS[data_split]['features_prefix'] + str(q_iid).zfill(12) + '.jpg.npz')['x']
                t_ivec = ( t_ivec / np.sqrt((t_ivec**2).sum()) )
            except:
                t_ivec = 0.
                print 'data not found for qid : ', q_iid,  self.mode

            # convert answer to vec
            if self.mode == 'val' or self.mode == 'test-dev' or self.mode == 'test':
                q_ans_str = self.extract_answer(q_ans)
            else:
                q_ans_str = self.extract_answer_prob(q_ans)
            t_avec = self.answer_to_vec(q_ans_str)

            for k in range(config.NUM_DC):
                dc_list=VQADataProvider.seq_to_list(t_dclist[k])
                t_dcvec , t_dc_cvec , t_dc_glove_matrix=self.qlist_to_vec(self.max_length,dc_list)
                dcvec[i*config.NUM_DC+k,...]=t_dcvec
                dc_cvec[i*config.NUM_DC+k,...]=t_dc_cvec
                dc_glove_matrix[i*config.NUM_DC+k,...]=t_dc_glove_matrix

            qvec[i,...] = t_qvec
            cvec[i,...] = t_cvec
            ivec[i,...] = t_ivec
            avec[i,...] = t_avec
            glove_matrix[i,...] = t_glove_matrix

        return qvec,dcvec , cvec,dc_cvec , ivec, avec, glove_matrix, dc_glove_matrix


    def get_batch_vec(self):
        if self.batch_len is None:
            self.n_skipped = 0
            qid_list = self.getQuesIds()
            random.shuffle(qid_list)
            self.qid_list = qid_list
            self.batch_len = len(qid_list)
            self.batch_index = 0
            self.epoch_counter = 0

        def has_at_least_one_valid_answer(t_qid):
            answer_obj = self.getAnsObj(t_qid)
            answer_list = [ans['answer'] for ans in answer_obj]
            for ans in answer_list:
                if self.adict.has_key(ans):
                    return True

        counter = 0
        t_qid_list = []
        t_iid_list = []
        while counter < self.batchsize:
            t_qid = self.qid_list[self.batch_index]
            t_iid = self.getImgId(t_qid)
            if self.mode == 'val' or self.mode == 'test-dev' or self.mode == 'test':
                t_qid_list.append(t_qid)
                t_iid_list.append(t_iid)
                counter += 1
            elif has_at_least_one_valid_answer(t_qid):
                t_qid_list.append(t_qid)
                t_iid_list.append(t_iid)
                counter += 1
            else:
                self.n_skipped += 1

            if self.batch_index < self.batch_len-1:
                self.batch_index += 1
            else:
                self.epoch_counter += 1
                qid_list = self.getQuesIds()
                random.shuffle(qid_list)
                self.qid_list = qid_list
                self.batch_index = 0
                print("%d questions were skipped in a single epoch" % self.n_skipped)
                self.n_skipped = 0

        t_batch = self.create_batch(t_qid_list)
        return t_batch + (t_qid_list, t_iid_list, self.epoch_counter)


class VQADataProviderLayer(caffe.Layer):
    """
    Provide input data for VQA.
    """

    def setup(self, bottom, top):
        self.batchsize = json.loads(self.param_str)['batchsize']
        self.top_names = ['data','dc_data','cont','dc_cont','feature','label','glove','dc_glove']
        top[0].reshape(15,self.batchsize)
        top[1].reshape(15,self.batchsize*config.NUM_DC)
        top[2].reshape(15,self.batchsize)
        top[3].reshape(15,self.batchsize*config.NUM_DC)
        top[4].reshape(self.batchsize,2048,14,14)
        top[5].reshape(self.batchsize)
        top[6].reshape(15,self.batchsize,GLOVE_EMBEDDING_SIZE)
        top[7].reshape(15,self.batchsize*config.NUM_DC,GLOVE_EMBEDDING_SIZE)
        self.mode = json.loads(self.param_str)['mode']
        if self.mode == 'val' or self.mode == 'test-dev' or self.mode == 'test':
            pass
        else:
            self.dp = VQADataProvider(batchsize=self.batchsize, mode=self.mode)

    def reshape(self, bottom, top):
        pass

    def forward(self, bottom, top):
        if self.mode == 'val' or self.mode == 'test-dev' or self.mode == 'test':
            pass
        else:
            word,dc_word, cont,dc_cont , feature, answer, glove_matrix,dc_glove_matrix,_,_,_ = self.dp.get_batch_vec()
            top[0].data[...] = np.transpose(word,(1,0)) # N x T -> T x N
            top[1].data[...] = np.transpose(dc_word,(1,0)) # N x T -> T x N
            top[2].data[...] = np.transpose(cont,(1,0))
            top[3].data[...] = np.transpose(dc_cont,(1,0))
            top[4].data[...] = feature
            top[5].data[...] = answer
            top[6].data[...] = np.transpose(glove_matrix, (1,0,2)) # N x T x 300 -> T x N x 300

            top[7].data[...] = np.transpose(dc_glove_matrix, (1,0,2)) # N x T x 300 -> T x N x 300
    def backward(self, top, propagate_down, bottom):
        pass

