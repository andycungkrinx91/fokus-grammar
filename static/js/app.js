document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const generateBtn = document.getElementById('generateBtn');
    const difficultySelect = document.getElementById('difficultySelect');
    const topicInput = document.getElementById('topicInput');
    const questionCountInput = document.getElementById('questionCount');
    const questionCard = document.getElementById('questionCard');
    const questionText = document.getElementById('questionText');
    const questionTopic = document.getElementById('questionTopic');
    const questionDifficulty = document.getElementById('questionDifficulty');
    const optionsContainer = document.getElementById('options');
    const checkAnswerBtn = document.getElementById('checkAnswerBtn');
    const feedbackCard = document.getElementById('feedbackCard');
    const feedbackHeader = document.getElementById('feedbackHeader');
    const feedbackContent = document.getElementById('feedbackContent');
    const explanationContent = document.getElementById('explanationContent');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorAlert = document.getElementById('errorAlert');
    const toggleQuestionBtn = document.getElementById('toggleQuestionBtn');
    const playAudioBtn = document.getElementById('playAudioBtn');
    const questionAudio = document.getElementById('questionAudio');
    const audioContainer = document.getElementById('audioContainer');
    const audioStatus = document.getElementById('audioStatus');

    // Questions data
    let questions = [];
    let currentQuestionIndex = 0;
    let currentQuestion = null;
    let selectedAnswer = null;
    let userAnswers = {}; // Store answers for all questions

    // Event Listeners
    generateBtn.addEventListener('click', generateQuestion);
    checkAnswerBtn.addEventListener('click', checkAnswer);
    toggleQuestionBtn.addEventListener('click', toggleQuestionText);
    playAudioBtn.addEventListener('click', playQuestionAudio);

    // Initialize by loading existing questions
    loadQuestions();
    
    // Function to toggle question text visibility
    function toggleQuestionText() {
        if (questionText.classList.contains('d-none')) {
            questionText.classList.remove('d-none');
            toggleQuestionBtn.innerHTML = '<i class="bi bi-eye-slash"></i> Hide Question';
        } else {
            questionText.classList.add('d-none');
            toggleQuestionBtn.innerHTML = '<i class="bi bi-eye"></i> Show Question';
        }
    }
    
    // Function to play question audio
    function playQuestionAudio() {
        if (currentQuestion && currentQuestion.audio_url) {
            questionAudio.play();
        }
    }
    
    // Function to check if audio is ready and update UI
    function checkAudioReady(audioUrl) {
        if (!audioUrl) return;
        
        const filename = audioUrl.split('/').pop();
        
        // Show audio status
        audioStatus.classList.remove('d-none');
        playAudioBtn.disabled = true;
        
        // Check if audio is ready every second
        const checkInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/check-audio/${filename}`);
                const data = await response.json();
                
                if (data.ready) {
                    // Audio is ready, update UI
                    clearInterval(checkInterval);
                    audioStatus.classList.add('d-none');
                    audioContainer.classList.remove('d-none');
                    playAudioBtn.disabled = false;
                    
                    // Set audio source
                    questionAudio.src = audioUrl;
                    questionAudio.load();
                }
            } catch (error) {
                console.error('Error checking audio status:', error);
            }
        }, 1000);
    }

    // Functions
    async function loadQuestions() {
        try {
            const response = await fetch('/api/questions');
            const questions = await response.json();
            console.log(`Loaded ${questions.length} questions`);
        } catch (error) {
            console.error('Error loading questions:', error);
        }
    }

    async function generateQuestion() {
        // Reset UI
        resetUI();
        showLoading(true);

        try {
            const difficulty = difficultySelect.value;
            const topic = topicInput.value.trim();
            const count = parseInt(questionCountInput.value) || 1;
            
            // Clear previous questions
            questions = [];
            currentQuestionIndex = 0;
            
            // Show progress message
            errorAlert.textContent = `Generating ${count} question(s)... Please wait.`;
            errorAlert.className = 'alert alert-info';
            errorAlert.classList.remove('d-none');
            
            // Generate all questions in a single request
            const response = await fetch('/api/generate-questions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ difficulty, topic, count })
            });

            const data = await response.json();

            if (data.success && data.questions && data.questions.length > 0) {
                questions = data.questions;
                // Hide progress message
                errorAlert.classList.add('d-none');
                
                // Create container for all questions
                const allQuestionsContainer = document.createElement('div');
                allQuestionsContainer.id = 'allQuestionsContainer';
                
                // Add all questions to the container
                questions.forEach((question, index) => {
                    const questionDiv = createQuestionElement(question, index);
                    allQuestionsContainer.appendChild(questionDiv);
                });
                
                // Add the container to the page
                const container = document.querySelector('.col-md-8.offset-md-2');
                container.appendChild(allQuestionsContainer);
                
                // Show submit all button in fixed position at bottom
                const submitAllDiv = document.createElement('div');
                submitAllDiv.id = 'submitAllContainer';
                submitAllDiv.className = 'fixed-bottom-container';
                submitAllDiv.innerHTML = `
                    <div class="container">
                        <div class="row">
                            <div class="col-md-8 offset-md-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span id="answersProgress" class="text-muted">0/${questions.length} questions answered</span>
                                    <button id="submitAllBtn" class="btn btn-primary btn-lg" disabled>Submit All Answers</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(submitAllDiv);
                
                // Add event listener to submit all button
                document.getElementById('submitAllBtn').addEventListener('click', submitAllAnswers);
            } else {
                showError('Failed to generate questions: ' + (data.error || 'Unknown error'));
                console.error('Error details:', data);
            }
        } catch (error) {
            showError('Error communicating with server');
            console.error('Error generating question:', error);
        } finally {
            showLoading(false);
        }
    }

    function createQuestionElement(question, index) {
        // Create question card
        const questionDiv = document.createElement('div');
        questionDiv.className = 'card mb-4 fade-in';
        questionDiv.id = `question-card-${question.id}`;
        
        // Set difficulty badge color
        let badgeClass = 'bg-secondary';
        if (question.difficulty === 'easy') {
            badgeClass = 'bg-success';
        } else if (question.difficulty === 'medium') {
            badgeClass = 'bg-warning';
        } else if (question.difficulty === 'hard') {
            badgeClass = 'bg-danger';
        }
        
        // Create card header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'card-header d-flex justify-content-between align-items-center';
        headerDiv.innerHTML = `
            <span class="badge bg-info topic-badge" data-topic="${question.grammar_topic}" role="button">${question.grammar_topic}</span>
            <span class="badge ${badgeClass}">${question.difficulty.charAt(0).toUpperCase() + question.difficulty.slice(1)}</span>
        `;
        questionDiv.appendChild(headerDiv);
        
        // Add click event to topic badge after it's added to the DOM
        setTimeout(() => {
            const topicBadge = questionDiv.querySelector('.topic-badge');
            if (topicBadge) {
                topicBadge.addEventListener('click', function() {
                    showGrammarTopicInfo(this.getAttribute('data-topic'));
                });
            }
        }, 0);
        
        // Create card body
        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'card-body';
        
        // Add audio controls and question toggle
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'd-flex justify-content-between align-items-center mb-3';
        
        // Controls container
        const buttonsDiv = document.createElement('div');
        
        // Toggle question button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'btn btn-sm btn-outline-secondary me-2';
        toggleBtn.innerHTML = '<i class="bi bi-eye"></i> Show Question';
        toggleBtn.addEventListener('click', function() {
            const questionTextEl = this.closest('.card-body').querySelector('.question-text');
            if (questionTextEl.classList.contains('d-none')) {
                questionTextEl.classList.remove('d-none');
                this.innerHTML = '<i class="bi bi-eye-slash"></i> Hide Question';
            } else {
                questionTextEl.classList.add('d-none');
                this.innerHTML = '<i class="bi bi-eye"></i> Show Question';
            }
        });
        buttonsDiv.appendChild(toggleBtn);
        
        // Play audio button
        const playBtn = document.createElement('button');
        playBtn.className = 'btn btn-sm btn-outline-primary';
        playBtn.innerHTML = '<i class="bi bi-volume-up"></i> Play Audio';
        playBtn.disabled = true; // Initially disabled until audio is ready
        
        // Audio status
        const statusDiv = document.createElement('div');
        statusDiv.className = 'text-muted small';
        statusDiv.innerHTML = '<i class="bi bi-hourglass-split"></i> Generating audio...';
        
        // Audio container
        const audioDiv = document.createElement('div');
        audioDiv.className = 'mb-3 d-none';
        const audio = document.createElement('audio');
        audio.controls = true;
        audio.className = 'w-100';
        audio.innerHTML = 'Your browser does not support the audio element.';
        audioDiv.appendChild(audio);
        
        // Set up audio if available
        if (question.audio_url) {
            // Function to check if audio is ready
            const checkAudio = async () => {
                const filename = question.audio_url.split('/').pop();
                try {
                    const response = await fetch(`/api/check-audio/${filename}`);
                    const data = await response.json();
                    
                    if (data.ready) {
                        statusDiv.classList.add('d-none');
                        audioDiv.classList.remove('d-none');
                        playBtn.disabled = false;
                        
                        // Set audio source
                        audio.src = question.audio_url;
                        audio.load();
                        
                        // Clear interval
                        clearInterval(checkInterval);
                    }
                } catch (error) {
                    console.error('Error checking audio status:', error);
                }
            };
            
            // Check audio status every second
            const checkInterval = setInterval(checkAudio, 1000);
            
            // Add play button event listener
            playBtn.addEventListener('click', function() {
                audio.play();
            });
            
            buttonsDiv.appendChild(playBtn);
            controlsDiv.appendChild(buttonsDiv);
            controlsDiv.appendChild(statusDiv);
            bodyDiv.appendChild(controlsDiv);
            bodyDiv.appendChild(audioDiv);
        } else {
            // No audio available
            buttonsDiv.appendChild(playBtn);
            controlsDiv.appendChild(buttonsDiv);
            bodyDiv.appendChild(controlsDiv);
        }
        
        // Add question number and text (initially hidden)
        const titleH5 = document.createElement('h5');
        titleH5.className = 'card-title mb-4 question-text d-none';
        titleH5.innerHTML = `<span class="badge bg-secondary me-2">${index + 1}</span> ${question.question}`;
        bodyDiv.appendChild(titleH5);
        
        // Create options container
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'mb-4';
        
        // Add options
        question.options.forEach((option, optIndex) => {
            const optionId = `question-${question.id}-option-${optIndex}`;
            const optionDiv = document.createElement('div');
            optionDiv.className = 'mb-3';
            optionDiv.innerHTML = `
                <input type="radio" name="answer-${question.id}" id="${optionId}" class="option-input" value="${option}">
                <label for="${optionId}" class="option-label">${option}</label>
            `;
            optionsDiv.appendChild(optionDiv);

            // Add event listener to each option
            const input = optionDiv.querySelector('input');
            input.addEventListener('change', function() {
                // Store the answer for this question
                userAnswers[question.id] = this.value;
                
                // Enable submit all button if we have answers for all questions
                updateSubmitAllButton();
                
                // Show feedback for this question if needed
                const feedbackDiv = document.getElementById(`feedback-${question.id}`);
                if (feedbackDiv) {
                    feedbackDiv.classList.add('d-none');
                }
            });
            
            // Check if we already have an answer for this question
            if (userAnswers[question.id] === option) {
                input.checked = true;
            }
        });
        
        bodyDiv.appendChild(optionsDiv);
        
        // Add feedback container (initially hidden)
        const feedbackDiv = document.createElement('div');
        feedbackDiv.id = `feedback-${question.id}`;
        feedbackDiv.className = 'd-none';
        bodyDiv.appendChild(feedbackDiv);
        
        questionDiv.appendChild(bodyDiv);
        return questionDiv;
    }

    async function checkAnswer() {
        if (!selectedAnswer || !currentQuestion) return;

        showLoading(true);
        feedbackCard.classList.add('d-none');

        try {
            const response = await fetch('/api/check-answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question_id: currentQuestion.id,
                    answer: selectedAnswer
                })
            });

            const data = await response.json();

            if (data.success) {
                displayFeedback(data);
                
                // Add navigation buttons if there are multiple questions
                if (questions.length > 1) {
                    addNavigationButtons();
                }
            } else {
                showError('Failed to check answer: ' + (data.error || 'Unknown error'));
                console.error('Error details:', data);
            }
        } catch (error) {
            showError('Error communicating with server');
            console.error('Error checking answer:', error);
        } finally {
            showLoading(false);
        }
    }
    
    function updateSubmitAllButton() {
        const submitAllBtn = document.getElementById('submitAllBtn');
        const progressSpan = document.getElementById('answersProgress');
        if (!submitAllBtn || !progressSpan) return;
        
        // Check if we have answers for all questions
        const answeredCount = Object.keys(userAnswers).length;
        const totalCount = questions.length;
        
        // Enable button if all questions are answered
        submitAllBtn.disabled = answeredCount < totalCount;
        
        // Update progress text
        progressSpan.textContent = `${answeredCount}/${totalCount} questions answered`;
        
        // Highlight questions that need answers
        questions.forEach(question => {
            const questionCard = document.getElementById(`question-card-${question.id}`);
            if (questionCard) {
                if (userAnswers[question.id]) {
                    // Question is answered, remove highlight
                    questionCard.classList.remove('border-warning');
                    questionCard.classList.add('border-success');
                } else {
                    // Question is not answered, add highlight
                    questionCard.classList.remove('border-success');
                    questionCard.classList.add('border-warning');
                }
            }
        });
        
        // Update button appearance based on progress
        if (answeredCount === totalCount) {
            submitAllBtn.classList.remove('btn-primary');
            submitAllBtn.classList.add('btn-success');
            submitAllBtn.innerHTML = `<i class="bi bi-check-circle-fill"></i> Submit All Answers`;
        } else {
            submitAllBtn.classList.remove('btn-success');
            submitAllBtn.classList.add('btn-primary');
            submitAllBtn.textContent = `Submit All Answers`;
        }
    }
    
    async function submitAllAnswers() {
        if (Object.keys(userAnswers).length < questions.length) {
            showError('Please answer all questions before submitting');
            return;
        }
        
        showLoading(true);
        
        // Prepare answers in the format expected by the API
        const answers = [];
        for (const [questionId, answer] of Object.entries(userAnswers)) {
            answers.push({
                question_id: parseInt(questionId),
                answer: answer
            });
        }
        
        try {
            const response = await fetch('/api/check-answers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ answers })
            });

            const data = await response.json();

            if (data.success && data.results) {
                displayAllResults(data.results);
            } else {
                showError('Failed to check answers: ' + (data.error || 'Unknown error'));
                console.error('Error details:', data);
            }
        } catch (error) {
            showError('Error communicating with server');
            console.error('Error checking answers:', error);
        } finally {
            showLoading(false);
        }
    }
    
    function displayAllResults(results) {
        // Hide questions container
        const questionsContainer = document.getElementById('allQuestionsContainer');
        if (questionsContainer) questionsContainer.remove();
        
        // Hide submit all button
        const submitAllDiv = document.getElementById('submitAllContainer');
        if (submitAllDiv) submitAllDiv.remove();
        
        // Create results container
        const resultsDiv = document.createElement('div');
        resultsDiv.id = 'resultsContainer';
        resultsDiv.className = 'mt-4';
        
        // Add header
        const header = document.createElement('h4');
        header.className = 'mb-4 text-center';
        header.textContent = 'Your Results';
        resultsDiv.appendChild(header);
        
        // Calculate score
        const correctCount = results.filter(r => r.is_correct).length;
        const totalCount = results.length;
        const scorePercent = Math.round((correctCount / totalCount) * 100);
        
        // Add score card
        const scoreCard = document.createElement('div');
        scoreCard.className = 'card mb-4';
        scoreCard.innerHTML = `
            <div class="card-body text-center">
                <h5 class="card-title">Your Score</h5>
                <div class="display-4 mb-3">${correctCount}/${totalCount} (${scorePercent}%)</div>
                <div class="progress">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${scorePercent}%" 
                        aria-valuenow="${scorePercent}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
        `;
        resultsDiv.appendChild(scoreCard);
        
        // Add each result
        results.forEach((result, index) => {
            // Find the corresponding question
            const question = questions.find(q => q.id === result.question_id);
            if (!question) return;
            
            const resultCard = document.createElement('div');
            resultCard.className = `card mb-3 ${result.is_correct ? 'border-success' : 'border-danger'}`;
            
            const headerClass = result.is_correct ? 'bg-success text-white' : 'bg-danger text-white';
            const headerText = result.is_correct ? '✓ Correct' : '✗ Incorrect';
            
            resultCard.innerHTML = `
                <div class="card-header ${headerClass} d-flex justify-content-between">
                    <span>${headerText}</span>
                    <span>${question.grammar_topic}</span>
                </div>
                <div class="card-body">
                    <h5 class="card-title">${question.question}</h5>
                    <p class="card-text">
                        <strong>Your answer:</strong> ${userAnswers[question.id]}<br>
                        <strong>Correct answer:</strong> ${result.correct_answer}
                    </p>
                    <div class="mt-3 pt-3 border-top">
                        <h6>Explanation:</h6>
                        <div class="language-tabs">
                            <ul class="nav nav-tabs" role="tablist">
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link active" id="explanation-english-tab-${result.question_id}" data-bs-toggle="tab" data-bs-target="#explanation-english-${result.question_id}" type="button" role="tab" aria-controls="explanation-english" aria-selected="true">
                                        <i class="bi bi-globe"></i> English
                                    </button>
                                </li>
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link" id="explanation-indonesian-tab-${result.question_id}" data-bs-toggle="tab" data-bs-target="#explanation-indonesian-${result.question_id}" type="button" role="tab" aria-controls="explanation-indonesian" aria-selected="false">
                                        <i class="bi bi-translate"></i> Bahasa Indonesia
                                    </button>
                                </li>
                            </ul>
                            <div class="tab-content mt-2">
                                <div class="tab-pane fade show active" id="explanation-english-${result.question_id}" role="tabpanel" aria-labelledby="explanation-english-tab">
                                    <p>${result.explanation_en || 'No explanation available in English.'}</p>
                                </div>
                                <div class="tab-pane fade" id="explanation-indonesian-${result.question_id}" role="tabpanel" aria-labelledby="explanation-indonesian-tab">
                                    <p>${result.explanation_id || 'Tidak ada penjelasan dalam Bahasa Indonesia.'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-top">
                        <h6>Feedback:</h6>
                        <div class="language-tabs">
                            <ul class="nav nav-tabs" role="tablist">
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link active" id="english-tab-${result.question_id}" data-bs-toggle="tab" data-bs-target="#english-${result.question_id}" type="button" role="tab" aria-controls="english" aria-selected="true">
                                        <i class="bi bi-globe"></i> English
                                    </button>
                                </li>
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link" id="indonesian-tab-${result.question_id}" data-bs-toggle="tab" data-bs-target="#indonesian-${result.question_id}" type="button" role="tab" aria-controls="indonesian" aria-selected="false">
                                        <i class="bi bi-translate"></i> Bahasa Indonesia
                                    </button>
                                </li>
                            </ul>
                            <div class="tab-content mt-2">
                                <div class="tab-pane fade show active" id="english-${result.question_id}" role="tabpanel" aria-labelledby="english-tab">
                                    <p>${result.feedback_en || 'No feedback available in English.'}</p>
                                </div>
                                <div class="tab-pane fade" id="indonesian-${result.question_id}" role="tabpanel" aria-labelledby="indonesian-tab">
                                    <p>${result.feedback_id || 'Tidak ada umpan balik dalam Bahasa Indonesia.'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            resultsDiv.appendChild(resultCard);
        });
        
        // Add try again button
        const tryAgainBtn = document.createElement('button');
        tryAgainBtn.className = 'btn btn-primary d-block mx-auto mt-4';
        tryAgainBtn.textContent = 'Generate New Questions';
        tryAgainBtn.addEventListener('click', generateQuestion);
        resultsDiv.appendChild(tryAgainBtn);
        
        // Add to page
        const container = document.querySelector('.col-md-8.offset-md-2');
        container.appendChild(resultsDiv);
    }
    
    function addNavigationButtons() {
        // Remove existing navigation if any
        const existingNav = document.getElementById('questionNavigation');
        if (existingNav) {
            existingNav.remove();
        }
        
        // Create navigation container
        const navDiv = document.createElement('div');
        navDiv.id = 'questionNavigation';
        navDiv.className = 'mt-4 d-flex justify-content-between';
        
        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'btn btn-outline-secondary';
        prevBtn.innerHTML = '&laquo; Previous';
        prevBtn.disabled = currentQuestionIndex === 0;
        prevBtn.addEventListener('click', () => navigateQuestions(-1));
        
        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'btn btn-outline-primary';
        nextBtn.innerHTML = 'Next &raquo;';
        nextBtn.disabled = currentQuestionIndex >= questions.length - 1;
        nextBtn.addEventListener('click', () => navigateQuestions(1));
        
        // Add buttons to container
        navDiv.appendChild(prevBtn);
        navDiv.appendChild(nextBtn);
        
        // Add navigation to the page
        feedbackCard.after(navDiv);
    }
    
    function navigateQuestions(direction) {
        // Calculate new index
        const newIndex = currentQuestionIndex + direction;
        
        // Validate index
        if (newIndex < 0 || newIndex >= questions.length) return;
        
        // Update current index
        currentQuestionIndex = newIndex;
        
        // Update question counter
        const counterDiv = document.getElementById('questionCounter');
        if (counterDiv) {
            counterDiv.innerHTML = `<span class="badge bg-secondary">Question ${currentQuestionIndex + 1} of ${questions.length}</span>`;
        }
        
        // Hide feedback and reset UI
        feedbackCard.classList.add('d-none');
        const navDiv = document.getElementById('questionNavigation');
        if (navDiv) navDiv.remove();
        
        // Display the new question
        displayQuestion(questions[currentQuestionIndex]);
    }

    function displayFeedback(data) {
        // Set feedback header
        if (data.is_correct) {
            feedbackHeader.textContent = 'Correct! 🎉';
            feedbackHeader.className = 'card-header correct';
            feedbackCard.className = 'card mb-4 correct';
        } else {
            feedbackHeader.textContent = 'Incorrect ❌';
            feedbackHeader.className = 'card-header incorrect';
            feedbackCard.className = 'card mb-4 incorrect';
        }

        // Set feedback content
        feedbackContent.innerHTML = data.feedback;
        explanationContent.innerHTML = `<h6>Explanation:</h6><p>${data.explanation}</p>`;

        // Show feedback card with animation
        feedbackCard.classList.remove('d-none');
        feedbackCard.classList.add('fade-in');
    }

    function resetUI() {
        // Hide error alert
        errorAlert.classList.add('d-none');
        
        // Reset user answers
        userAnswers = {};
        
        // Remove questions container if exists
        const questionsContainer = document.getElementById('allQuestionsContainer');
        if (questionsContainer) questionsContainer.remove();
        
        // Remove submit all button if exists
        const submitAllDiv = document.getElementById('submitAllContainer');
        if (submitAllDiv) submitAllDiv.remove();
        
        // Remove results container if exists
        const resultsContainer = document.getElementById('resultsContainer');
        if (resultsContainer) resultsContainer.remove();
    }

    function showLoading(isLoading) {
        // Remove existing fixed loading if any
        const existingFixedLoading = document.getElementById('fixedLoadingSpinner');
        if (existingFixedLoading) {
            existingFixedLoading.remove();
        }
        
        if (isLoading) {
            // Create fixed position loading spinner
            const fixedLoading = document.createElement('div');
            fixedLoading.id = 'fixedLoadingSpinner';
            fixedLoading.className = 'fixed-feedback alert alert-info text-center';
            fixedLoading.innerHTML = `
                <div class="d-flex align-items-center justify-content-center">
                    <div class="spinner-border text-primary me-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>Processing your request... Please wait.</span>
                </div>
            `;
            document.body.appendChild(fixedLoading);
            
            // Disable buttons
            generateBtn.disabled = true;
            const submitAllBtn = document.getElementById('submitAllBtn');
            if (submitAllBtn) submitAllBtn.disabled = true;
        } else {
            // Enable buttons
            generateBtn.disabled = false;
            // Update submit button state based on answers
            updateSubmitAllButton();
        }
    }

        function showError(message) {
        // Remove existing fixed error if any
        const existingFixedError = document.getElementById('fixedErrorAlert');
        if (existingFixedError) {
            existingFixedError.remove();
        }
        
        // Create fixed position error alert
        const fixedError = document.createElement('div');
        fixedError.id = 'fixedErrorAlert';
        fixedError.className = 'fixed-feedback alert alert-danger';
        fixedError.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" aria-label="Close"></button>
            </div>
        `;
        document.body.appendChild(fixedError);
        
        // Add event listener to close button
        fixedError.querySelector('.btn-close').addEventListener('click', function() {
            fixedError.remove();
        });
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (fixedError.parentNode) {
                fixedError.remove();
            }
        }, 5000);
    }
    
    async function showGrammarTopicInfo(topic) {
        // Remove existing modal if any
        const existingModal = document.getElementById('grammarTopicModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Create modal
        const modalHTML = `
            <div class="modal fade" id="grammarTopicModal" tabindex="-1" aria-labelledby="grammarTopicModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="grammarTopicModalLabel">
                                <i class="bi bi-book"></i> ${topic}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div id="grammarTopicLoading" class="text-center">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading grammar information...</p>
                            </div>
                            <div id="grammarTopicContent" class="d-none">
                                <ul class="nav nav-tabs" role="tablist">
                                    <li class="nav-item" role="presentation">
                                        <button class="nav-link active" id="topic-english-tab" data-bs-toggle="tab" data-bs-target="#topic-english" type="button" role="tab" aria-controls="topic-english" aria-selected="true">
                                            <i class="bi bi-globe"></i> English
                                        </button>
                                    </li>
                                    <li class="nav-item" role="presentation">
                                        <button class="nav-link" id="topic-indonesian-tab" data-bs-toggle="tab" data-bs-target="#topic-indonesian" type="button" role="tab" aria-controls="topic-indonesian" aria-selected="false">
                                            <i class="bi bi-translate"></i> Bahasa Indonesia
                                        </button>
                                    </li>
                                </ul>
                                <div class="tab-content mt-3">
                                    <div class="tab-pane fade show active" id="topic-english" role="tabpanel" aria-labelledby="topic-english-tab">
                                        <div id="topic-english-content"></div>
                                    </div>
                                    <div class="tab-pane fade" id="topic-indonesian" role="tabpanel" aria-labelledby="topic-indonesian-tab">
                                        <div id="topic-indonesian-content"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to body
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer.firstElementChild);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('grammarTopicModal'));
        modal.show();
        
        // Fetch grammar topic information from AI
        try {
            const response = await fetch('/api/grammar-topic-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ topic })
            });

            const data = await response.json();
            
            // Hide loading, show content
            document.getElementById('grammarTopicLoading').classList.add('d-none');
            document.getElementById('grammarTopicContent').classList.remove('d-none');
            
            if (data.success) {
                // Render Markdown content
                document.getElementById('topic-english-content').innerHTML = marked.parse(data.english_content);
                document.getElementById('topic-indonesian-content').innerHTML = marked.parse(data.indonesian_content);
                
                // Add styling to the rendered content
                const styleElements = () => {
                    const contentDivs = [
                        document.getElementById('topic-english-content'),
                        document.getElementById('topic-indonesian-content')
                    ];
                    
                    contentDivs.forEach(div => {
                        // Style headings
                        div.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
                            heading.classList.add('mt-3', 'mb-2');
                        });
                        
                        // Style code blocks and examples
                        div.querySelectorAll('pre, code').forEach(code => {
                            code.classList.add('p-2', 'bg-light', 'rounded');
                        });
                        
                        // Style lists
                        div.querySelectorAll('ul, ol').forEach(list => {
                            list.classList.add('my-2');
                        });
                        
                        // Style tables if any
                        div.querySelectorAll('table').forEach(table => {
                            table.classList.add('table', 'table-bordered', 'my-3');
                        });
                    });
                };
                
                // Apply styles after a short delay to ensure content is rendered
                setTimeout(styleElements, 100);
                
                // Show cached indicator if applicable
                if (data.cached) {
                    const cachedIndicator = document.createElement('div');
                    cachedIndicator.className = 'alert alert-info mt-2 mb-3';
                    cachedIndicator.innerHTML = `
                        <div class="d-flex align-items-center">
                            <i class="bi bi-database-check me-2"></i>
                            <span>Information loaded from cache</span>
                        </div>
                    `;
                    document.getElementById('grammarTopicContent').prepend(cachedIndicator);
                }
            } else {
                // Show error in the modal
                document.getElementById('topic-english-content').innerHTML = `<div class="alert alert-warning">Failed to load grammar information: ${data.error || 'Unknown error'}</div>`;
                document.getElementById('topic-indonesian-content').innerHTML = `<div class="alert alert-warning">Gagal memuat informasi tata bahasa: ${data.error || 'Kesalahan tidak diketahui'}</div>`;
            }
        } catch (error) {
            // Hide loading, show content with error
            document.getElementById('grammarTopicLoading').classList.add('d-none');
            document.getElementById('grammarTopicContent').classList.remove('d-none');
            
            // Show error in the modal
            document.getElementById('topic-english-content').innerHTML = `<div class="alert alert-danger">Error loading grammar information: ${error.message}</div>`;
            document.getElementById('topic-indonesian-content').innerHTML = `<div class="alert alert-danger">Terjadi kesalahan saat memuat informasi tata bahasa: ${error.message}</div>`;
        }
    }
});
