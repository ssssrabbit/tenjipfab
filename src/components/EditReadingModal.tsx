import React, { useState, useEffect } from 'react';
import {
  Modal, View, Text, TextInput, Pressable, StyleSheet, KeyboardAvoidingView, Platform,
} from 'react-native';
import { AppColors } from '../constants/colors';

interface Props {
  visible: boolean;
  origWord: string;
  currentReading: string;
  onClose: () => void;
  onSave: (newReading: string) => void;
}

export default function EditReadingModal({ visible, origWord, currentReading, onClose, onSave }: Props) {
  const [reading, setReading] = useState(currentReading);

  useEffect(() => {
    if (visible) setReading(currentReading);
  }, [visible, currentReading]);

  function handleSave() {
    onSave(reading);
    onClose();
  }

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={styles.overlay}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.dialog}>
          <Text style={styles.title}>「{origWord}」の読みを修正</Text>

          <TextInput
            style={styles.input}
            value={reading}
            onChangeText={setReading}
            placeholder="読み（ひらがな）"
            placeholderTextColor={AppColors.TEXT_SUB}
            autoFocus
            returnKeyType="done"
            onSubmitEditing={handleSave}
          />

          <View style={styles.actions}>
            <Pressable onPress={onClose} style={styles.actionBtn}>
              <Text style={[styles.actionText, styles.cancelText]}>キャンセル</Text>
            </Pressable>
            <Pressable onPress={handleSave} style={styles.actionBtn}>
              <Text style={styles.actionText}>保存</Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  dialog: {
    width: '82%',
    backgroundColor: AppColors.SURFACE,
    borderRadius: 14,
    padding: 20,
  },
  title: {
    fontSize: 17,
    fontWeight: '600',
    color: AppColors.TEXT_MAIN,
    marginBottom: 16,
  },
  input: {
    borderWidth: 1,
    borderColor: AppColors.DIVIDER,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    color: AppColors.TEXT_MAIN,
    backgroundColor: AppColors.BACKGROUND,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 16,
    gap: 4,
  },
  actionBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  actionText: {
    fontSize: 16,
    color: AppColors.PRIMARY,
    fontWeight: '500',
  },
  cancelText: {
    color: AppColors.TEXT_SUB,
  },
});
