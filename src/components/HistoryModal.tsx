import React from 'react';
import {
  Modal, View, Text, Pressable, StyleSheet, FlatList, Alert,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { AppColors } from '../constants/colors';
import { HistoryEntry } from '../stores/historyStore';

interface Props {
  visible: boolean;
  history: HistoryEntry[];
  onClose: () => void;
  onRestore: (item: HistoryEntry) => void;
  onClear: () => void;
}

export default function HistoryModal({ visible, history, onClose, onRestore, onClear }: Props) {
  function handleClear() {
    Alert.alert('履歴のクリア', '全履歴を消去しますか？', [
      { text: 'キャンセル', style: 'cancel' },
      {
        text: 'クリア', style: 'destructive',
        onPress: () => { onClear(); onClose(); },
      },
    ]);
  }

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.dialog}>
          <Text style={styles.title}>履歴 (最新{history.length}件)</Text>

          {history.length === 0 ? (
            <Text style={styles.empty}>履歴はありません</Text>
          ) : (
            <FlatList
              data={history}
              keyExtractor={(_, i) => String(i)}
              style={styles.list}
              renderItem={({ item }) => {
                const preview = item.text.length > 15
                  ? item.text.slice(0, 15) + '...'
                  : item.text;
                const meta = `${item.timestamp} | ${item.maxCharsPerLine}文字/${item.maxLinesPerPlate}行/${item.plateThickness}mm`;
                return (
                  <Pressable
                    style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
                    onPress={() => { onRestore(item); onClose(); }}
                  >
                    <MaterialIcons name="history" size={22} color={AppColors.TEXT_SUB} style={styles.icon} />
                    <View style={styles.itemText}>
                      <Text style={styles.itemTitle}>{preview}</Text>
                      <Text style={styles.itemMeta}>{meta}</Text>
                    </View>
                  </Pressable>
                );
              }}
              ItemSeparatorComponent={() => <View style={styles.separator} />}
            />
          )}

          <View style={styles.actions}>
            <Pressable onPress={handleClear} style={styles.actionBtn}>
              <Text style={[styles.actionText, styles.clearText]}>クリア</Text>
            </Pressable>
            <Pressable onPress={onClose} style={styles.actionBtn}>
              <Text style={styles.actionText}>閉じる</Text>
            </Pressable>
          </View>
        </View>
      </View>
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
    width: '88%',
    backgroundColor: AppColors.SURFACE,
    borderRadius: 14,
    padding: 20,
    maxHeight: '70%',
  },
  title: {
    fontSize: 17,
    fontWeight: '600',
    color: AppColors.TEXT_MAIN,
    marginBottom: 12,
  },
  empty: {
    textAlign: 'center',
    color: AppColors.TEXT_SUB,
    paddingVertical: 24,
  },
  list: {
    maxHeight: 320,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
  },
  itemPressed: {
    backgroundColor: AppColors.HOVER_BG,
    borderRadius: 8,
  },
  icon: {
    marginRight: 10,
  },
  itemText: {
    flex: 1,
  },
  itemTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: AppColors.TEXT_MAIN,
  },
  itemMeta: {
    fontSize: 12,
    color: AppColors.TEXT_SUB,
    marginTop: 2,
  },
  separator: {
    height: 1,
    backgroundColor: AppColors.DIVIDER,
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
  clearText: {
    color: AppColors.ERROR,
  },
});
