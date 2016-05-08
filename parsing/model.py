from parsing.action import Actions
from parsing.config import Config


class Model(object):
    def __init__(self, model_type=None, labels=None, features=None, model=None):
        self._update_only_on_error = None
        self.model_type = model_type
        if features is not None and model is not None:
            self.features = features
            self.model = model
            return

        if model_type == "sparse":
            from classifiers.sparse_perceptron import SparsePerceptron
            from features.sparse_features import SparseFeatureExtractor
            self.features = SparseFeatureExtractor()
            self.model = SparsePerceptron(labels, min_update=Config().min_update)
        elif model_type == "dense":
            from features.embedding import FeatureEmbedding
            from classifiers.dense_perceptron import DensePerceptron
            self.features = self.dense_features_wrapper(FeatureEmbedding)
            self.model = DensePerceptron(labels, num_features=self.features.num_features())
        elif model_type == "nn":
            from features.indexer import FeatureIndexer
            from classifiers.neural_network import NeuralNetwork
            self.features = self.dense_features_wrapper(FeatureIndexer)
            self.model = NeuralNetwork(labels, inputs=self.features.feature_types,
                                       layers=Config().layers,
                                       layer_dim=Config().layer_dim,
                                       activation=Config().activation,
                                       init=Config().init,
                                       max_num_labels=Config().max_num_labels,
                                       batch_size=Config().batch_size,
                                       minibatch_size=Config().minibatch_size,
                                       nb_epochs=Config().nb_epochs,
                                       optimizer=Config().optimizer,
                                       loss=Config().loss
                                       )
        else:
            raise ValueError("Invalid model type: '%s'" % model_type)

    @staticmethod
    def dense_features_wrapper(wrapper):
        from features.dense_features import DenseFeatureExtractor
        return wrapper(DenseFeatureExtractor(),
                       w=(Config().word_vectors, 10000),
                       t=(Config().tag_dim, 100),
                       e=(Config().label_dim, 15),
                       p=(Config().punct_dim, 5),
                       x=(Config().gap_dim, 3),
                       )

    def extract_features(self, *args, **kwargs):
        return self.features.extract_features(*args, **kwargs)

    def score(self, *args, **kwargs):
        return self.model.score(*args, **kwargs)

    def update(self, *args, **kwargs):
        self.model.update(*args, **kwargs)

    @property
    def update_only_on_error(self):
        if self._update_only_on_error is None:
            self._update_only_on_error = self.model_type in ("sparse", "dense")
        return self._update_only_on_error

    def finalize(self, *args, **kwargs):
        return Model(model_type=self.model_type,
                     features=self.features.finalize(*args, **kwargs),
                     model=self.model.finalize(*args, **kwargs))

    def save(self, *args, **kwargs):
        self.features.save(*args, **kwargs)
        self.model.save(*args, **kwargs)

    def load(self, *args, **kwargs):
        self.features.load(*args, **kwargs)
        self.model.load(*args, **kwargs)
        Actions().all = self.model.labels
