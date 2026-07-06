import { useState } from 'react';
import { StyleSheet, Text, View, Pressable } from 'react-native';

const questions = [
  {
    question: 'What is the capital of France?',
    options: ['Paris', 'London', 'Berlin'],
    correctAnswer: 'Paris',
  },
  {
    question: 'Which planet is known as the Red Planet?',
    options: ['Earth', 'Mars', 'Jupiter'],
    correctAnswer: 'Mars',
  },
  {
    question: 'What is 2 + 2?',
    options: ['3', '4', '5'],
    correctAnswer: '4',
  },
];

export default function App() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [quizFinished, setQuizFinished] = useState(false);

  const currentQuestion = questions[currentIndex];

  const handleSelect = (option) => {
    if (selected) return;
    setSelected(option);
    if (option === currentQuestion.correctAnswer) {
      setScore(score + 1);
    }
  };

  const handleNext = () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex < questions.length) {
      setCurrentIndex(nextIndex);
      setSelected(null);
    } else {
      setQuizFinished(true);
    }
  };

  const handleRestart = () => {
    setCurrentIndex(0);
    setSelected(null);
    setScore(0);
    setQuizFinished(false);
  };

  if (quizFinished) {
    return (
      <View style={styles.container}>
        <Text style={styles.question}>Quiz Complete!</Text>
        <Text style={styles.result}>
          Your score: {score} / {questions.length}
        </Text>
        <Pressable style={styles.nextButton} onPress={handleRestart}>
          <Text style={styles.nextButtonText}>Restart Quiz</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.progress}>
        Question {currentIndex + 1} / {questions.length}
      </Text>
      <Text style={styles.question}>{currentQuestion.question}</Text>

      {currentQuestion.options.map((option) => {
        const isSelected = selected === option;
        const isCorrect = option === currentQuestion.correctAnswer;

        let optionStyle = styles.option;
        if (selected) {
          if (isCorrect) {
            optionStyle = [styles.option, styles.correctOption];
          } else if (isSelected) {
            optionStyle = [styles.option, styles.wrongOption];
          }
        }

        return (
          <Pressable
            key={option}
            style={optionStyle}
            onPress={() => handleSelect(option)}
          >
            <Text style={styles.optionText}>{option}</Text>
          </Pressable>
        );
      })}

      {selected && (
        <Pressable style={styles.nextButton} onPress={handleNext}>
          <Text style={styles.nextButtonText}>
            {currentIndex + 1 < questions.length ? 'Next' : 'See Results'}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'white',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  progress: {
    fontSize: 14,
    color: 'gray',
    marginBottom: 10,
  },
  question: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 30,
    textAlign: 'center',
  },
  option: {
    backgroundColor: '#eeeeee',
    padding: 15,
    borderRadius: 10,
    marginVertical: 8,
    width: '100%',
  },
  correctOption: {
    backgroundColor: '#a5e8a5',
  },
  wrongOption: {
    backgroundColor: '#f5a5a5',
  },
  optionText: {
    fontSize: 18,
    textAlign: 'center',
  },
  result: {
    marginTop: 10,
    marginBottom: 30,
    fontSize: 20,
    fontWeight: 'bold',
  },
  nextButton: {
    backgroundColor: '#333333',
    padding: 15,
    borderRadius: 10,
    marginTop: 20,
    width: '100%',
  },
  nextButtonText: {
    color: 'white',
    fontSize: 18,
    textAlign: 'center',
    fontWeight: 'bold',
  },
});