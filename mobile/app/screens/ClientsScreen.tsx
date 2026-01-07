import { useEffect, useState } from 'react';
import { ScrollScreen, ScreenHeader, VStack, HStack, Text, Badge, Card, Input, List, ListItem, Button, Section, StatsCards, StatCard } from '../../_components/ui';
import { useClientsStore } from '../stores';
import { Client, formatCurrency, formatDate } from '../../data/mockData';
import { View, StyleSheet } from 'react-native';
import { theme } from '../../theme';

function ClientListItem({ client, onPress }: { client: Client; onPress: () => void }) {
  const statusColors: Record<string, string> = {
    active: '#059669',
    inactive: '#64748B',
    prospect: '#D97706',
  };

  return (
    <ListItem
      title={client.name}
      subtitle={client.company}
      description={`${client.location} • Last contact: ${formatDate(client.lastContact)}`}
      badge={client.status}
      badgeColor={statusColors[client.status]}
      chevron
      onPress={onPress}
    />
  );
}

function ClientDetail({ client, onClose }: { client: Client; onClose: () => void }) {
  return (
    <View style={styles.detailContainer}>
      <ScreenHeader
        title={client.name}
        onBack={onClose}
        rightAction={
          <Button variant="ghost" size="sm" onPress={onClose}>
            ✕
          </Button>
        }
      />
      <ScrollScreen contentContainerStyle={styles.detailContent}>
        <VStack spacing="lg">
          <Card>
            <VStack spacing="md">
              <HStack justify="between">
                <Text color="muted">Company</Text>
                <Text weight="medium">{client.company}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Status</Text>
                <Badge color={client.status === 'active' ? 'success' : client.status === 'prospect' ? 'warning' : 'secondary'}>
                  {client.status}
                </Badge>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Location</Text>
                <Text>{client.location}</Text>
              </HStack>
            </VStack>
          </Card>

          <Card>
            <VStack spacing="md">
              <Text variant="h4" weight="semibold">Contact</Text>
              <HStack justify="between">
                <Text color="muted">Email</Text>
                <Text>{client.email}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Phone</Text>
                <Text>{client.phone}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Last Contact</Text>
                <Text>{formatDate(client.lastContact)}</Text>
              </HStack>
            </VStack>
          </Card>

          <Card>
            <VStack spacing="md">
              <Text variant="h4" weight="semibold">Revenue</Text>
              <HStack justify="between">
                <Text color="muted">Total Revenue</Text>
                <Text variant="h4" color="success">{formatCurrency(client.totalRevenue)}</Text>
              </HStack>
            </VStack>
          </Card>

          <HStack spacing="sm">
            <Button variant="secondary" fullWidth>
              Edit Client
            </Button>
            <Button variant="primary" fullWidth>
              Log Activity
            </Button>
          </HStack>
        </VStack>
      </ScrollScreen>
    </View>
  );
}

export default function ClientsScreen() {
  const { clients, filteredClients, searchQuery, statusFilter, selectedClient, isLoading, setSearchQuery, setStatusFilter, selectClient, loadClients } = useClientsStore();
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  const handleClientPress = (client: Client) => {
    selectClient(client);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
  };

  if (showDetail && selectedClient) {
    return <ClientDetail client={selectedClient} onClose={handleCloseDetail} />;
  }

  const activeClients = clients.filter((c) => c.status === 'active');
  const totalRevenue = clients.reduce((sum, c) => sum + c.totalRevenue, 0);
  const prospectClients = clients.filter((c) => c.status === 'prospect');

  return (
    <ScrollScreen
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      <ScreenHeader title="Clients" subtitle={`${clients.length} total`} />

      <VStack spacing="md" style={styles.content}>
        <Input
          placeholder="Search clients..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          size="md"
        />

        <HStack spacing="sm">
          {(['all', 'active', 'prospect', 'inactive'] as const).map((status) => (
            <Button
              key={status}
              variant={statusFilter === status ? 'primary' : 'secondary'}
              size="sm"
              onPress={() => setStatusFilter(status)}
              style={{ flex: 1 }}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Button>
          ))}
        </HStack>

        <StatsCards style={styles.statsContainer}>
          <StatCard label="Active" value={activeClients.length} color="success" />
          <StatCard label="Revenue" value={formatCurrency(totalRevenue).replace('$', '')} color="info" />
          <StatCard label="Prospects" value={prospectClients.length} color="warning" />
        </StatsCards>

        <Section title={`Clients (${filteredClients.length})`}>
          <List variant="inset">
            {filteredClients.map((client) => (
              <ClientListItem
                key={client.id}
                client={client}
                onPress={() => handleClientPress(client)}
              />
            ))}
          </List>
        </Section>
      </VStack>
    </ScrollScreen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xxl,
  },
  statsContainer: {
    marginTop: theme.spacing.sm,
  },
  detailContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  detailContent: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xxl,
  },
});
