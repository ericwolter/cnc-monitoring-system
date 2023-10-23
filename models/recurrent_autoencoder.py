from torch import nn


class Encoder(nn.Module):
    def __init__(self, seq_len, n_features, embedding_dim=64):
        super(Encoder, self).__init__()

        self.seq_len, self.n_features = seq_len, n_features
        self.embedding_dim, self.hidden_dim = embedding_dim, 2 * embedding_dim

        self.rnn1 = nn.LSTM(
            input_size=n_features,
            hidden_size=self.hidden_dim,
            num_layers=1,
            batch_first=True,
        )

        self.rnn2 = nn.LSTM(
            input_size=self.hidden_dim,
            hidden_size=embedding_dim,
            num_layers=1,
            batch_first=True,
        )

    def forward(self, x):
        # Input shape: (batch_size, seq_len, n_features)

        # Pass through RNN1
        # Output shape: (batch_size, seq_len, hidden_dim)
        x, (_, _) = self.rnn1(x)

        # Pass through RNN2
        # Output shape: (batch_size, seq_len, embedding_dim)
        # hidden_n shape: (1, batch_size, embedding_dim)
        x, (hidden_n, _) = self.rnn2(x)

        # We're only interested in the last hidden state for encoding,
        # so we reshape to maintain batch size
        # Output shape: (batch_size, embedding_dim)
        return hidden_n.reshape((self.n_features, self.embedding_dim))


class Decoder(nn.Module):
    def __init__(self, seq_len, input_dim=64, n_features=1):
        super(Decoder, self).__init__()

        self.seq_len, self.input_dim = seq_len, input_dim
        self.hidden_dim, self.n_features = 2 * input_dim, n_features

        self.rnn1 = nn.LSTM(
            input_size=input_dim, hidden_size=input_dim, num_layers=1, batch_first=True
        )

        self.rnn2 = nn.LSTM(
            input_size=input_dim,
            hidden_size=self.hidden_dim,
            num_layers=1,
            batch_first=True,
        )

        self.output_layer = nn.Linear(self.hidden_dim, n_features)

    def forward(self, x):
        # Input shape: (batch_size, embedding_dim)

        # Repeat and reshape the input tensor to have shape
        # (batch_size, seq_len, input_dim) for LSTM input
        # Essentially, it "broadcasts" the encoded representation to each time step in the sequence.
        x = x.repeat(self.seq_len, self.n_features)
        x = x.reshape((self.n_features, self.seq_len, self.input_dim))

        # Pass through RNN1
        # Output shape: (batch_size, seq_len, input_dim)
        x, (_, _) = self.rnn1(x)

        # Pass through RNN2
        # Output shape: (batch_size, seq_len, hidden_dim)
        x, (_, _) = self.rnn2(x)

        # Apply the linear transformation to produce the final output.
        # This maps the hidden states to the desired number of features.
        # Output shape: (batch_size, seq_len, n_features)
        x = self.output_layer(x)

        return x


class RecurrentAutoencoder(nn.Module):
    def __init__(self, seq_len, n_features, embedding_dim=64):
        super(RecurrentAutoencoder, self).__init__()

        self.encoder = Encoder(seq_len, n_features, embedding_dim)
        self.decoder = Decoder(seq_len, embedding_dim, n_features)

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)

        return x
