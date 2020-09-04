
# remove all conda environments named "benchopt_*"
clean-conda:
	conda info --envs | grep benchopt_ | \
		awk '{print $$1}' | xargs -i conda env remove -n {}

