import React from 'react';

interface ErrorMessageProps {
  message: string;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => {
  return (
    <p className="text-center text-red-500 font-medium bg-red-100 border border-red-300 rounded-md p-2">
      {message}
    </p>
  );
};

export default ErrorMessage;