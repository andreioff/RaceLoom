FROM python:3.12.11-bookworm

WORKDIR /raceloom

# Install OpenJDK-18 for KATch
RUN apt-get update && \
    apt-get install -y openjdk-17-jdk && \
    apt-get clean;

# Copy KATch folder and test the tool
COPY bin bin 
RUN test $(bin/katch/test_katch.sh) = "OK!"

# Copy source files
COPY src src
COPY main.py main.py
COPY pyproject.toml pyproject.toml

# Install dependencies
RUN pip3 install .

# Copy other relevant files
COPY examples examples

# Run shell
CMD ["/bin/bash"]
